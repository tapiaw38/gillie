from pydantic import BaseModel
from typing import List


class RoleOutputData(BaseModel):
    code: str
    name: str


class RoleOutput(BaseModel):
    data: RoleOutputData
    @staticmethod
    def from_output(role):
        return RoleOutput(
            data=RoleOutputData(
                code=role.code,
                name=role.name,
            )
        )


class ListOptionsOutputData(BaseModel):
    """Output data structure for role list options"""
    roles: List[RoleOutputData]


class ListOptionsOutput(BaseModel):
    """Main output structure for role list options"""
    data: ListOptionsOutputData
    @staticmethod
    def from_output(roles: List):
        role_data = []
        for role in roles:
            role_data.append(
                RoleOutputData(
                    code=role.code,
                    name=role.name,
                )
            )

        return ListOptionsOutput(data=ListOptionsOutputData(roles=role_data))
