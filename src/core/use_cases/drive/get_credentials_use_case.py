from typing import Optional
from src.core.platform.appcontext.appcontext import Factory


class GetCredentialsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory()

    def execute(self) -> Optional[dict]:
        creds = self.context_factory.repositories.drive.find_credentials()
        if not creds:
            return None
        return {
            "client_id": creds.client_id,
            "redirect_uri": creds.redirect_uri,
            "has_secret": bool(creds.client_secret),
        }
