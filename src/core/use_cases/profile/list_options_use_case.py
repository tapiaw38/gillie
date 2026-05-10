from src.schemas import (
    ListOptionsOutput,
    ListOptionsOutputData,
    RoleOutputData,
    ProviderOutputData,
)
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.config.service import get_available_providers, get_active_provider_name
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.common import DatabaseQueryError


class ListOptionsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, user_id: str = "") -> ListOptionsOutput:
        try:
            context = self.context_factory()
            roles = context.repositories.role.get_all_roles()

            role_data = []
            for role in roles:
                role_data.append(
                    RoleOutputData(
                        code=role.code,
                        name=role.name,
                    )
                )

            profile = None
            if user_id:
                profile = await context.repositories.profile.find_by_user_id(user_id)

            provider_keys = (profile.provider_keys or {}) if profile else None
            custom_providers = (profile.custom_providers or {}) if profile else None
            active_provider = (profile.active_provider or "") if profile else ""

            provider_data = [
                ProviderOutputData(
                    key=key,
                    model=preset["model"],
                    base_url=preset.get("base_url", ""),
                    auth_type=preset.get("auth_type", "api_key"),
                    api_key_set=bool(preset.get("api_key")),
                    is_builtin=preset.get("is_builtin", True),
                )
                for key, preset in get_available_providers(
                    provider_keys=provider_keys,
                    custom_providers=custom_providers,
                ).items()
            ]

            list_options_data = ListOptionsOutputData(
                roles=role_data,
                providers=provider_data,
                active_provider=get_active_provider_name(active_provider),
            )

            return ListOptionsOutput(data=list_options_data)

        except PyMongoError as e:
            raise NewApplicationError(DatabaseQueryError, e)
