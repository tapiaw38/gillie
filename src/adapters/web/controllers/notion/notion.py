from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse

from src.adapters.web.dependencies import get_usecases
from src.core.use_cases.use_cases import Usecases
from src.schemas.notion import (
    NotionAuthorizationOutput,
    NotionCredentialsInput,
    NotionPageResponse,
    NotionSearchResponse,
    NotionStatusOutput,
)

router = APIRouter(prefix="/api/v1/notion", tags=["notion"])


@router.get("/credentials", status_code=status.HTTP_200_OK)
async def get_notion_credentials(usecases: Usecases = Depends(get_usecases)):
    return await usecases.notion.get_credentials_usecase.execute() or {}


@router.post("/credentials", status_code=status.HTTP_200_OK)
async def set_notion_credentials(
    creds: NotionCredentialsInput,
    usecases: Usecases = Depends(get_usecases),
):
    redirect_uri = creds.redirect_uri or "http://localhost:8000/api/v1/notion/oauth/callback"
    await usecases.notion.set_credentials_usecase.execute(
        creds.client_id,
        creds.client_secret,
        redirect_uri,
    )
    return {"message": "Credentials saved successfully"}


@router.get("/authorize", response_model=NotionAuthorizationOutput, status_code=status.HTTP_200_OK)
async def get_authorization_url(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id")
    auth_url = await usecases.notion.get_authorization_url_usecase.execute(user_id)
    return NotionAuthorizationOutput(authorization_url=auth_url, user_id=user_id)


@router.get("/oauth/callback", response_class=HTMLResponse)
async def oauth_callback(
    request: Request,
    code: str,
    state: Optional[str] = None,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = state or request.state.user.get("user_id")
    await usecases.notion.handle_oauth_callback_usecase.execute(user_id, code)
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head><title>Authorization successful</title></head>
<body>
<p>Authorization successful. Closing window...</p>
<script>
  if (window.opener) {
    try { window.opener.postMessage({ type: 'oauth_success', integration: 'notion' }, '*'); } catch(e) {}
  }
  window.close();
</script>
</body>
</html>
""")


@router.get("/status", response_model=NotionStatusOutput, status_code=status.HTTP_200_OK)
async def check_notion_status(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id")
    return NotionStatusOutput(
        **(await usecases.notion.check_session_status_usecase.execute(user_id))
    )


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_notion(
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id")
    await usecases.notion.disconnect_usecase.execute(user_id)


@router.get("/search", response_model=NotionSearchResponse, status_code=status.HTTP_200_OK)
async def search_notion_pages(
    request: Request,
    query: str = "",
    page_size: int = 20,
    start_cursor: Optional[str] = None,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id")
    payload = await usecases.notion.search_pages_usecase.execute(
        user_id,
        query=query,
        page_size=page_size,
        start_cursor=start_cursor,
    )
    return NotionSearchResponse(
        results=payload.get("results", []),
        next_cursor=payload.get("next_cursor"),
        has_more=payload.get("has_more", False),
    )


@router.get("/pages/{page_id}", response_model=NotionPageResponse, status_code=status.HTTP_200_OK)
async def get_notion_page(
    page_id: str,
    request: Request,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id")
    return NotionPageResponse(
        data=await usecases.notion.get_page_usecase.execute(user_id, page_id)
    )


@router.get("/pages/{page_id}/content", response_model=NotionPageResponse, status_code=status.HTTP_200_OK)
async def get_notion_page_content(
    page_id: str,
    request: Request,
    max_depth: int = 4,
    usecases: Usecases = Depends(get_usecases),
):
    user_id = request.state.user.get("user_id")
    return NotionPageResponse(
        data=await usecases.notion.get_page_content_usecase.execute(
            user_id,
            page_id,
            max_depth=max_depth,
        )
    )
