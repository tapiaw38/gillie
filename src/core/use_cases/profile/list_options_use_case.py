from src.schemas import (
    ListOptionsOutput,
    ListOptionsOutputData,
    RoleOutputData,
)
from src.core.platform.appcontext.appcontext import Factory


class ListOptionsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self) -> ListOptionsOutput:
        roles = self.context_factory.repositories.role.get_all_roles()

        print(f"Roles found: {len(roles)}")
        role_data = []
        for role in roles:
            role_data.append(
                RoleOutputData(
                    code=role.code,
                    name=role.name,
                )
            )
        list_options_data = ListOptionsOutputData(roles=role_data)

        return ListOptionsOutput(data=list_options_data)