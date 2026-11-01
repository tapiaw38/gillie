"""The conversation repository's contract with its Mongo client.

Rewritten against the current design. The previous version was written for a
`Repository(client=...)` with synchronous methods that reached for
`client.insert_one` itself; today the repository takes a `Datasources` and is
async throughout, and a driver error is wrapped in an ApplicationError rather
than escaping raw. None of that could be reached by fixing imports, and the
module had stopped importing at all, which aborted collection for the whole
suite.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pymongo.errors import PyMongoError

from src.adapters.datasources.datasources import Datasources
from src.adapters.datasources.repositories.conversation.repository import Repository
from src.core.domain import Conversation, Profile
from src.core.platform.errors import ApplicationError


@pytest.fixture
def client():
    """A double for the conversations client, async where the real one is.

    `find` is the exception: on the real client it returns a cursor
    synchronously, and only `to_list` is awaited. Leaving it as an AsyncMock
    hands the repository a coroutine to call `.sort()` on.
    """
    double = AsyncMock()
    double.find = MagicMock()
    return double


@pytest.fixture
def repository(client):
    datasources = Datasources(
        no_sql_conversations_client=client,
        no_sql_profiles_client=AsyncMock(),
        no_sql_faqs_client=AsyncMock(),
    )
    return Repository(datasources)


def build_conversation(**kwargs) -> Conversation:
    defaults = {
        "id": str(uuid4()),
        "title": "Test Conversation",
        "created_at": datetime.now(timezone.utc),
        "client_id": "client-1",
        "profile": Profile(user_id="123"),
    }
    defaults.update(kwargs)
    return Conversation(**defaults)


def cursor_over(documents: list):
    """Stand in for `client.find(...).sort(...)`, which returns a cursor.

    `find` and `sort` are synchronous on the real client and only `to_list` is
    awaited, so a plain MagicMock with one AsyncMock on it mirrors that shape.
    """
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.to_list = AsyncMock(return_value=documents)
    return cursor


@pytest.mark.asyncio
async def test_create_returns_the_id_mongo_assigned(repository, client):
    conversation = build_conversation()
    client.insert_one.return_value = MagicMock(inserted_id="generated-id")

    created_id = await repository.create(conversation)

    assert created_id == "generated-id"
    client.insert_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_wraps_a_driver_error_as_an_application_error(repository, client):
    """The contract the error handler depends on.

    Letting a PyMongoError through would surface to the caller as an
    unclassified 500 with the driver's own wording, instead of the mapped
    conversation error code.
    """
    client.insert_one.side_effect = PyMongoError("connection lost")

    with pytest.raises(ApplicationError) as raised:
        await repository.create(build_conversation())

    assert raised.value.internal_code() == "conversation:create:query-error"


@pytest.mark.asyncio
async def test_find_by_id_builds_the_domain_model(repository, client):
    created_at = datetime.now(timezone.utc)
    client.find_one.return_value = {
        "_id": "abc",
        "title": "Stored",
        "created_at": created_at,
        "client_id": "client-1",
        "profile": {"user_id": "123"},
    }

    found = await repository.find_by_id("abc")

    assert isinstance(found, Conversation)
    assert found.id == "abc"
    assert found.title == "Stored"


@pytest.mark.asyncio
async def test_find_by_id_returns_none_when_there_is_no_document(repository, client):
    client.find_one.return_value = None

    assert await repository.find_by_id("missing") is None


@pytest.mark.asyncio
async def test_find_by_user_id_leaves_sandbox_conversations_out_by_default(
    repository, client
):
    """Sandbox conversations are the CLI's scratch threads. Listing them
    alongside real ones is what the `is_sandbox` filter exists to prevent, and
    the default has to be the safe one since most callers pass nothing."""
    client.find.return_value = cursor_over([])

    await repository.find_user_id("123")

    query_filter = client.find.call_args.args[0]
    assert query_filter["profile.user_id"] == "123"
    assert query_filter["is_sandbox"] == {"$ne": True}


@pytest.mark.asyncio
async def test_find_by_user_id_includes_them_when_asked(repository, client):
    client.find.return_value = cursor_over([])

    await repository.find_user_id("123", include_sandbox=True)

    assert "is_sandbox" not in client.find.call_args.args[0]


@pytest.mark.asyncio
async def test_find_by_user_id_counts_the_messages_it_loaded(repository, client):
    """`message_count` is derived on read rather than stored, so a document
    written before the field existed still reports a usable count."""
    now = datetime.now(timezone.utc)
    client.find.return_value = cursor_over([
        {
            "_id": "abc",
            "title": "Stored",
            "created_at": now,
            "client_id": "client-1",
            "profile": {"user_id": "123"},
            "messages": [
                {"content": "one", "sender": "user", "created_at": now},
                {"content": "two", "sender": "assistant", "created_at": now},
            ],
        }
    ])

    conversations = await repository.find_user_id("123")

    assert len(conversations) == 1
    assert conversations[0].message_count == 2
