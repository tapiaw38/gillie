from typing import List
from src.core.domain import Profile
from src.core.platform.nosql.client import Client


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
    except Exception as e:
        raise Exception(f"Error al buscar todos los perfiles: {e}")
