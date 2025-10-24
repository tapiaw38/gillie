import pytest
from unittest.mock import MagicMock
from datetime import datetime
from uuid import uuid4
from src.adapters.datasources.repositories.faq.repository import Repository
from src.adapters.datasources.datasources import Datasources
from src.core.domain import FAQ


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def mock_datasources(mock_client):
    datasources = MagicMock(spec=Datasources)
    datasources.no_sql_faqs_client = mock_client
    return datasources


@pytest.fixture
def repository(mock_datasources):
    return Repository(datasources=mock_datasources)


def build_faq(**kwargs):
    defaults = {
        "id": str(uuid4()),
        "profile_id": str(uuid4()),
        "question": "What is Python?",
        "answer": "Python is a programming language",
        "category": "Programming",
        "tags": ["python", "programming"],
        "is_active": True,
        "order": 1,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    defaults.update(kwargs)
    return FAQ(**defaults)


def test_create_faq_success(repository, mock_client):
    """Test successful FAQ creation"""
    faq = build_faq()
    mock_client.insert_one.return_value.inserted_id = faq.id

    result = repository.create(faq)

    assert result == faq.id
    mock_client.insert_one.assert_called_once()


def test_create_faq_failure(repository, mock_client):
    """Test FAQ creation failure"""
    faq = build_faq()
    mock_client.insert_one.side_effect = Exception("Database error")

    with pytest.raises(Exception):
        repository.create(faq)


def test_find_by_id_success(repository, mock_client):
    """Test finding FAQ by ID successfully"""
    faq = build_faq()
    mock_faq_dict = faq.dict(by_alias=True)
    mock_faq_dict["_id"] = faq.id
    mock_client.find_one.return_value = mock_faq_dict

    result = repository.find_by_id(faq.id)

    assert result is not None
    assert result.question == faq.question
    mock_client.find_one.assert_called_once()


def test_find_by_id_not_found(repository, mock_client):
    """Test finding FAQ by ID when not found"""
    mock_client.find_one.return_value = None

    result = repository.find_by_id("nonexistent_id")

    assert result is None


def test_find_all_success(repository, mock_client):
    """Test finding all FAQs for a profile"""
    profile_id = str(uuid4())
    faq1 = build_faq(profile_id=profile_id, question="Question 1")
    faq2 = build_faq(profile_id=profile_id, question="Question 2")

    mock_faqs = [
        {**faq1.dict(by_alias=True), "_id": faq1.id},
        {**faq2.dict(by_alias=True), "_id": faq2.id}
    ]

    mock_cursor = MagicMock()
    mock_cursor.__iter__.return_value = iter(mock_faqs)
    mock_cursor.sort.return_value = mock_cursor
    mock_client.find.return_value = mock_cursor

    result = repository.find_all(profile_id)

    assert len(result) == 2
    assert result[0].question == "Question 1"
    assert result[1].question == "Question 2"


def test_find_all_with_filters(repository, mock_client):
    """Test finding FAQs with profile_id, category and is_active filters"""
    mock_cursor = MagicMock()
    mock_cursor.__iter__.return_value = iter([])
    mock_cursor.sort.return_value = mock_cursor
    mock_client.find.return_value = mock_cursor

    profile_id = str(uuid4())
    repository.find_all(profile_id=profile_id, category="Programming", is_active=True)

    mock_client.find.assert_called_once()
    call_args = mock_client.find.call_args[0][0]
    assert call_args["profile_id"] == profile_id
    assert call_args["category"] == "Programming"
    assert call_args["is_active"] is True


def test_update_faq_success(repository, mock_client):
    """Test updating FAQ successfully"""
    faq = build_faq()
    mock_client.update_one.return_value.matched_count = 1

    result = repository.update(faq.id, faq)

    assert result == faq.id
    mock_client.update_one.assert_called_once()


def test_update_faq_not_found(repository, mock_client):
    """Test updating FAQ when not found"""
    faq = build_faq()
    mock_client.update_one.return_value.matched_count = 0

    with pytest.raises(Exception) as exc_info:
        repository.update(faq.id, faq)

    assert "not found" in str(exc_info.value)


def test_delete_faq_success(repository, mock_client):
    """Test deleting FAQ successfully"""
    faq_id = str(uuid4())
    mock_client.delete_one.return_value.deleted_count = 1

    result = repository.delete(faq_id)

    assert result is True
    mock_client.delete_one.assert_called_once()


def test_delete_faq_not_found(repository, mock_client):
    """Test deleting FAQ when not found"""
    faq_id = str(uuid4())
    mock_client.delete_one.return_value.deleted_count = 0

    result = repository.delete(faq_id)

    assert result is False


def test_find_by_category_success(repository, mock_client):
    """Test finding FAQs by profile_id and category"""
    profile_id = str(uuid4())
    faq1 = build_faq(profile_id=profile_id, category="Python")
    faq2 = build_faq(profile_id=profile_id, category="Python")

    mock_faqs = [
        {**faq1.dict(by_alias=True), "_id": faq1.id},
        {**faq2.dict(by_alias=True), "_id": faq2.id}
    ]

    mock_cursor = MagicMock()
    mock_cursor.__iter__.return_value = iter(mock_faqs)
    mock_cursor.sort.return_value = mock_cursor
    mock_client.find.return_value = mock_cursor

    result = repository.find_by_category(profile_id, "Python")

    assert len(result) == 2
    assert all(faq.category == "Python" for faq in result)
    mock_client.find.assert_called_once()
