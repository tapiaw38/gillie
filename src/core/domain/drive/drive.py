from pydantic import BaseModel


class DriveCredentials(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8000/api/v1/drive/oauth/callback"
