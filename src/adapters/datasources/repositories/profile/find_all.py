from typing import List
from pymongo.errors import PyMongoError
from src.core.domain import Profile
from src.core.platform.nosql.client import Client
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.profile import ProfileListQueryError


def find_all(client: Client) -> List[Profile]:
    """
    Encuentra todos los perfiles
    """
    try:
        # El cliente ya apunta a la colección "profiles", podemos usar find() directamente
        profiles_data = list(client.find({}))

        profiles = []
        for profile_data in profiles_data:
            profile = Profile(**profile_data)
            profiles.append(profile)

        return profiles
    except PyMongoError as e:
        raise NewApplicationError(ProfileListQueryError, e)
