from src.schemas.schemas import ProfileOutput
from pymongo.errors import PyMongoError
from src.core.platform.appcontext.appcontext import Factory


class FindByUserIdUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self, user_id: str):
        try:
            profile = self.context_factory.repositories.profile.find_by_user_id(user_id)
            if not profile:
                raise Exception(f"No profile found with user_id: {user_id}")
            return ProfileOutput.from_output(profile)

        except PyMongoError as e:
            raise Exception(f"Error interacting with database: {e}")

        except Exception as e:
            raise Exception(f"Error executing FindByUserIdUseCase: {e}")