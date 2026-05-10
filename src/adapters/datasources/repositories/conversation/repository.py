from typing import List, Optional
from src.core.domain import (
    Conversation,
    Message,
    Profile,
)
from src.adapters.datasources.datasources import Datasources
from pymongo.errors import PyMongoError
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.conversation import (
    ConversationCreateQueryError,
    ConversationGetQueryError,
    ConversationListQueryError,
    ConversationUpdateQueryError,
)
from .repository_interface import RepositoryInterface


class Repository(RepositoryInterface):
    def __init__(self, datasources: Datasources):
        self.client = datasources.no_sql_conversations_client

    async def create(self, conversation: Conversation) -> str:
        try:
            conversation_dict = conversation.dict(by_alias=True, exclude_none=True, exclude_unset=True)
            result = await self.client.insert_one(conversation_dict)
            return str(result.inserted_id)
        except PyMongoError as exc:
            raise NewApplicationError(ConversationCreateQueryError, exc)

    async def find_by_id(self, id: str) -> Optional[Conversation]:
        try:
            document = await self.client.find_one({"_id": id})
            if document:
                return Conversation(**document)
            return None
        except PyMongoError as exc:
            raise NewApplicationError(ConversationGetQueryError, exc)

    async def find_user_id(self, user_id: str, include_sandbox: bool = False) -> List[Conversation]:
        try:
            query_filter = {"profile.user_id": user_id}
            if not include_sandbox:
                query_filter["is_sandbox"] = {"$ne": True}

            cursor = self.client.find(query_filter).sort("created_at", -1)
            documents = await cursor.to_list(length=None)
            return [
                Conversation(
                    **{
                        **doc,
                        "id": str(doc["_id"]),
                        "message_count": len(doc.get("messages", [])),
                    }
                )
                for doc in documents
            ]
        except PyMongoError as exc:
            raise NewApplicationError(ConversationListQueryError, exc)

    async def find_sandbox_by_user_id(self, user_id: str) -> List[Conversation]:
        try:
            query_filter = {"profile.user_id": user_id, "is_sandbox": True}
            cursor = self.client.find(query_filter).sort("created_at", -1)
            documents = await cursor.to_list(length=None)
            return [
                Conversation(
                    **{
                        **doc,
                        "id": str(doc["_id"]),
                        "message_count": len(doc.get("messages", [])),
                    }
                )
                for doc in documents
            ]
        except PyMongoError as exc:
            raise NewApplicationError(ConversationListQueryError, exc)

    async def update_profile_by_user_id(self, user_id: str, profile: Profile) -> str:
        try:
            profile_dict = profile.dict(by_alias=True, exclude_none=True, exclude_unset=True)
            result = await self.client.update_many(
                {"profile.user_id": user_id},
                {"$set": {"profile": profile_dict}},
            )
            return str(result.modified_count)
        except PyMongoError as exc:
            raise NewApplicationError(ConversationUpdateQueryError, exc)

    async def update_messages_by_id(self, id: str, messages: List[Message]) -> None:
        try:
            messages_dict = [message.dict(by_alias=True, exclude_none=True, exclude_unset=True) for message in messages]
            await self.client.update_one({"_id": id}, {"$set": {"messages": messages_dict}})
        except PyMongoError as exc:
            raise NewApplicationError(ConversationUpdateQueryError, exc)

    async def delete_by_id(self, id: str) -> None:
        try:
            await self.client.delete_one({"_id": id})
        except PyMongoError as exc:
            raise NewApplicationError(ConversationUpdateQueryError, exc)

    async def update_summary(self, conversation_id: str, summary: str, memory_extracted: bool = True) -> None:
        try:
            await self.client.update_one(
                {"_id": conversation_id},
                {"$set": {"summary": summary, "memory_extracted": memory_extracted}},
            )
        except PyMongoError as exc:
            raise NewApplicationError(ConversationUpdateQueryError, exc)

    async def find_unextracted(self, user_id: str) -> List[Conversation]:
        try:
            cursor = self.client.find(
                {
                    "profile.user_id": user_id,
                    "summary": {"$exists": True, "$nin": ["", None]},
                    "$or": [
                        {"memory_extracted": {"$exists": False}},
                        {"memory_extracted": False},
                    ],
                }
            ).sort("created_at", 1)
            documents = await cursor.to_list(length=None)
            return [Conversation(**doc) for doc in documents]
        except PyMongoError as exc:
            raise NewApplicationError(ConversationListQueryError, exc)
