from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse
from typing import List, Optional

from src.schemas.gmail import (
    GmailCredentialsInput,
    GmailEmailOutput,
    GmailEmailListOutput,
    GmailSendEmailInput,
    GmailReplyEmailInput,
    GmailAuthorizationOutput,
    GmailStatusOutput,
)
from src.core.use_cases.use_cases import Usecases
from src.adapters.web.dependencies import get_usecases
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/gmail",
    tags=["gmail"],
)


@router.get("/credentials", status_code=status.HTTP_200_OK)
async def get_gmail_credentials(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Get saved Gmail OAuth credentials (client_id only, secret never returned)."""
    return usecases.gmail.get_credentials_usecase.execute() or {}


@router.post("/credentials", status_code=status.HTTP_200_OK)
async def set_gmail_credentials(
    creds: GmailCredentialsInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Save Google OAuth2 app credentials (client_id / client_secret) to MongoDB."""
    redirect_uri = creds.redirect_uri or "http://localhost:8000/api/v1/gmail/oauth/callback"
    usecases.gmail.set_credentials_usecase.execute(
        client_id=creds.client_id,
        client_secret=creds.client_secret,
        redirect_uri=redirect_uri,
    )
    return {"message": "Credentials saved successfully"}


@router.get("/authorize", response_model=GmailAuthorizationOutput, status_code=status.HTTP_200_OK)
async def get_authorization_url(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Get Gmail OAuth authorization URL for the current user."""
    user_id = request.state.user.get("user_id")
    auth_url = usecases.gmail.get_authorization_url_usecase.execute(user_id)
    return GmailAuthorizationOutput(
        authorization_url=auth_url,
        user_id=user_id,
    )


@router.get("/oauth/callback", response_class=HTMLResponse)
async def oauth_callback(
    request: Request,
    code: str,
    state: Optional[str] = None,
    usecases: Usecases = Depends(get_usecases),
):
    """
    Handle Google OAuth2 callback for Gmail.
    Google redirects here after the user grants access.
    `state` carries the user_id set during authorization.
    Returns an HTML page that closes the popup window.
    """
    user_id = state or request.state.user.get("user_id")
    usecases.gmail.handle_oauth_callback_usecase.execute(user_id=user_id, code=code)
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head><title>Autorización exitosa</title></head>
<body>
<p>Autorización exitosa. Cerrando ventana...</p>
<script>
  if (window.opener) {
    try { window.opener.postMessage({ type: 'oauth_success', integration: 'gmail' }, '*'); } catch(e) {}
  }
  window.close();
</script>
</body>
</html>
""")


@router.get("/status", response_model=GmailStatusOutput, status_code=status.HTTP_200_OK)
async def check_gmail_status(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Check if the user has an active Gmail session."""
    user_id = request.state.user.get("user_id")
    is_active = usecases.gmail.check_session_status_usecase.execute(user_id)
    return GmailStatusOutput(
        is_active=is_active,
        user_id=user_id,
    )


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_gmail(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Disconnect (revoke) the Gmail OAuth session."""
    user_id = request.state.user.get("user_id")
    usecases.gmail.disconnect_usecase.execute(user_id)


@router.get("/emails", response_model=GmailEmailListOutput, status_code=status.HTTP_200_OK)
async def list_emails(
    request: Request,
    query: str = "",
    max_results: int = 20,
    label_ids: Optional[str] = None,
    usecases: Usecases = Depends(get_usecases),
):
    """List emails for the current user. Use `label_ids` as a comma-separated string (e.g. INBOX,UNREAD)."""
    user_id = request.state.user.get("user_id")
    parsed_label_ids = [l.strip() for l in label_ids.split(",")] if label_ids else None
    emails = usecases.gmail.list_emails_usecase.execute(
        user_id=user_id,
        query=query,
        max_results=max_results,
        label_ids=parsed_label_ids,
    )
    email_outputs = [GmailEmailOutput(**e) for e in emails]
    return GmailEmailListOutput(data=email_outputs, total=len(email_outputs))


@router.get("/emails/{message_id}", response_model=GmailEmailOutput, status_code=status.HTTP_200_OK)
async def get_email(
    message_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Get a single email by its Gmail message ID."""
    user_id = request.state.user.get("user_id")
    email = usecases.gmail.get_email_usecase.execute(user_id=user_id, message_id=message_id)
    return GmailEmailOutput(**email)


@router.post("/emails", status_code=status.HTTP_201_CREATED)
async def send_email(
    email_input: GmailSendEmailInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Send a new email."""
    user_id = request.state.user.get("user_id")
    result = usecases.gmail.send_email_usecase.execute(
        user_id=user_id,
        to=email_input.to,
        subject=email_input.subject,
        body=email_input.body,
        body_html=email_input.body_html,
        cc=email_input.cc,
        bcc=email_input.bcc,
    )
    return result


@router.post("/emails/{message_id}/reply", status_code=status.HTTP_201_CREATED)
async def reply_email(
    message_id: str,
    reply_input: GmailReplyEmailInput,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Reply to an existing email thread."""
    user_id = request.state.user.get("user_id")
    result = usecases.gmail.reply_email_usecase.execute(
        user_id=user_id,
        message_id=message_id,
        body=reply_input.body,
        body_html=reply_input.body_html,
    )
    return result


@router.delete("/emails/{message_id}", status_code=status.HTTP_200_OK)
async def delete_email(
    message_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Move an email to Trash."""
    user_id = request.state.user.get("user_id")
    usecases.gmail.delete_email_usecase.execute(user_id=user_id, message_id=message_id)
    return {"message": "Email moved to trash", "message_id": message_id}


@router.post("/emails/{message_id}/read", status_code=status.HTTP_200_OK)
async def mark_as_read(
    message_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Mark an email as read."""
    user_id = request.state.user.get("user_id")
    usecases.gmail.mark_email_read_usecase.execute(user_id=user_id, message_id=message_id)
    return {"message": "Email marked as read", "message_id": message_id}


@router.post("/emails/{message_id}/unread", status_code=status.HTTP_200_OK)
async def mark_as_unread(
    message_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    """Mark an email as unread."""
    user_id = request.state.user.get("user_id")
    usecases.gmail.mark_email_unread_usecase.execute(user_id=user_id, message_id=message_id)
    return {"message": "Email marked as unread", "message_id": message_id}
