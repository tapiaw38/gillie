from typing import List
from src.core.domain.model import Profile
from pymongo.database import Database


def find_all(client: Database) -> List[Profile]:
    """
    Encuentra todos los perfiles
    """
    try:
        profiles_collection = client["profiles"]
        profiles_data = list(profiles_collection.find())
        
        profiles = []
        for profile_data in profiles_data:
            profile = Profile(**profile_data)
            profiles.append(profile)
        
        return profiles
    except Exception as e:
        raise Exception(f"Error al buscar todos los perfiles: {e}")
