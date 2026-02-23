from src.adapters.datasources.datasources import Datasources
from .repository_interface import RepositoryInterface
from src.core.domain import (
    Profile,
    ApiKey,
    File,
    Integration,
)
from typing import List, Optional
from pymongo.errors import PyMongoError, DuplicateKeyError

from .create import create_profile
from .find_by_id import find_profile_by_id
from .find_by_user_id import find_profile_by_user_id
from .find_all_user_ids import find_all_user_ids
from .find_all import find_all
from .update import update_profile
from .update_api_keys import update_api_keys
from .deactivate_api_key import deactivate_api_key
from .find_by_api_key_value import find_by_api_key_value
from .update_iteration_limit import update_iteration_limit
from .update_files import update_files
from .delete_file_by_id import delete_file_by_id
from .get_file_by_id import get_file_by_id
from .update_integrations import update_integrations


class Repository(RepositoryInterface):
    def __init__(self, datasources: Datasources):
        self.client = datasources.no_sql_profiles_client
        self.client.create_index("user_id", unique=True)

    def create(self, profile: Profile) -> str:
        return create_profile(self.client, profile)

    def find_by_id(self, id: str) -> Optional[Profile]:
        return find_profile_by_id(self.client, id)

    def find_by_user_id(self, user_id: str) -> Profile:
        return find_profile_by_user_id(self.client, user_id)

    def find_all_user_ids(self) -> List[str]:
        return find_all_user_ids(self.client)

    def find_all(self) -> List[Profile]:
        return find_all(self.client)

    def update(self, id: str, profile: Profile) -> str:
        return update_profile(self.client, id, profile)

    def update_api_keys(self, user_id: str, api_keys: List[ApiKey]) -> None:
        update_api_keys(self.client, user_id, api_keys)

    def deactivate_api_key(self, user_id: str, api_key_id: str) -> Optional[str]:
        return deactivate_api_key(self.client, user_id, api_key_id)

    def find_by_api_key_value(self, user_id: str, api_key_value: str) -> ApiKey:
        return find_by_api_key_value(self.client, user_id, api_key_value)

    def update_iteration_limit(self, user_id: str, iteration_limit: int) -> str:
        return update_iteration_limit(self.client, user_id, iteration_limit)

    def update_files(self, user_id: str, files: List[File]) -> None:
        update_files(self.client, user_id, files)

    def delete_file_by_id(self, user_id: str, file_id: str) -> None:
        delete_file_by_id(self.client, user_id, file_id)

    def get_file_by_id(self, user_id: str, file_id: str) -> Optional[File]:
        return get_file_by_id(self.client, user_id, file_id)

    def update_integrations(self, user_id: str, integrations: List[Integration]) -> None:
        update_integrations(self.client, user_id, integrations)
