from pydantic import BaseModel, Field
from typing import Optional, List


class GmailCredentialsInput(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = None


class GmailEmailOutput(BaseModel):
    id: str
    thread_id: str = ""
    label_ids: List[str] = []
    snippet: str = ""
    from_: str = Field("", alias="from")
    to: str = ""
    cc: str = ""
    subject: str = ""
    date: str = ""
    body: str = ""
    is_read: bool = True

    class Config:
        populate_by_name = True


class GmailEmailListOutput(BaseModel):
    data: List[GmailEmailOutput]
    total: int = 0


class GmailSendEmailInput(BaseModel):
    to: str
    subject: str
    body: str
    body_html: Optional[str] = None
    cc: Optional[str] = None
    bcc: Optional[str] = None


class GmailReplyEmailInput(BaseModel):
    body: str
    body_html: Optional[str] = None


class GmailAuthorizationOutput(BaseModel):
    authorization_url: str
    user_id: str


class GmailStatusOutput(BaseModel):
    is_active: bool
    user_id: str
    email: Optional[str] = None
