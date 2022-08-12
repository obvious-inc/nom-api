import logging

from aioauth.utils import build_uri
from aioauth_fastapi.utils import to_fastapi_response
from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.dependencies import get_current_user
from app.helpers.auth import authorization_server, to_oauth2_request
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/authorize")
async def get_app_authorization_page(request: Request):
    query = dict(request.query_params)
    # TODO: better handle this...
    location = build_uri("http://localhost:8080/oauth/authorize", query, None)

    # TODO: still need to validate client id and so on...

    return RedirectResponse(location)


@router.post("/authorize")
async def post_app_authorization_page(request: Request, current_user: User = Depends(get_current_user)):
    oauth2_request = await to_oauth2_request(request, current_user=current_user)
    if not oauth2_request.query.channel:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing channel")

    consent = bool(int(oauth2_request.post.consent))
    if not consent:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Consent not granted")

    oauth2_response = await authorization_server.create_authorization_response(oauth2_request)
    return await to_fastapi_response(oauth2_response)


@router.post("/token")
async def create_access_token(request: Request, current_user: User = Depends(get_current_user)):
    oauth2_request = await to_oauth2_request(request, current_user=current_user)
    oauth2_response = await authorization_server.create_token_response(oauth2_request)
    return await to_fastapi_response(oauth2_response)
