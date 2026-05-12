from pydantic import BaseModel


class NotionCredentials(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8000/api/v1/notion/oauth/callback"
