"""
Role repository implementation with predefined roles
"""
from typing import List
from src.adapters.datasources.repositories.inmemory.repository import new_repository, Repository

class Role:
    """Role entity with a code and name"""
    def __init__(self, code: str, name: str):
        self.code = code
        self.name = name

    def get_code(self) -> str:
        return self.code


ASSISTANT_ROLE = Role("1", "assistant")
SELLER_ROLE = Role("2", "seller")
TUTOR_ROLE = Role("3", "tutor")


class RoleRepository:
    """Repository for managing roles with predefined data"""
    
    def __init__(self):
        self._predefined_roles: List[Role] = [
            ASSISTANT_ROLE,
            SELLER_ROLE, 
            TUTOR_ROLE
        ]
        self._repository: Repository[Role] = new_repository(self._predefined_roles)
    
    def get_all_roles(self) -> List[Role]:
        """Get all available roles"""
        return self._repository.list()
    
    def get_role_by_code(self, code: str) -> Role | None:
        """Get role by code (1, 2, or 3)"""
        return self._repository.get(code)
    
    def get_assistant_role(self) -> Role:
        """Get assistant role (code: 1)"""
        return ASSISTANT_ROLE
    
    def get_seller_role(self) -> Role:
        """Get seller role (code: 2)"""
        return SELLER_ROLE
    
    def get_tutor_role(self) -> Role:
        """Get tutor role (code: 3)"""
        return TUTOR_ROLE
    
    def is_valid_role_code(self, code: str) -> bool:
        """Check if the provided code is a valid role code"""
        return code in ["1", "2", "3"]


role_repository = RoleRepository()
