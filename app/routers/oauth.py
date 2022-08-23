import logging

from aioauth.utils import build_uri
from fastapi import APIRouter, Depends, HTTPException
from starlette import status
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.config import get_settings
from app.dependencies import get_current_client, get_current_user
from app.helpers.auth import authorization_server, to_fastapi_response, to_oauth2_request
from app.helpers.permissions import check_resource_permission
from app.models.channel import Channel
from app.models.user import User
from app.services.crud import get_item_by_id

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/authorize")
async def get_app_authorization_page(request: Request):
    settings = get_settings()
    query = dict(request.query_params)
    location = build_uri(url=f"{settings.frontend_url}/oauth/authorize", query_params=query)
    return RedirectResponse(location)


@router.post("/authorize")
async def post_app_authorization_page(request: Request, current_user: User = Depends(get_current_user)):
    oauth2_request = await to_oauth2_request(request, current_user=current_user)
    consent = bool(int(oauth2_request.post.consent)) if oauth2_request.post.consent else False
    if not consent:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Consent not granted")

    if not oauth2_request.query.channel:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing channel")
    channel = await get_item_by_id(id_=oauth2_request.query.channel, result_obj=Channel)
    await check_resource_permission(user=current_user, resource=channel, action="apps.manage")

    oauth2_response = await authorization_server.create_authorization_response(oauth2_request)
    if oauth2_response.status_code == status.HTTP_302_FOUND:
        location = oauth2_response.headers.get("location")
        return {"location": location}

    return await to_fastapi_response(oauth2_response)


@router.post("/token", dependencies=[Depends(get_current_client)])
async def create_access_token(request: Request):
    oauth2_request = await to_oauth2_request(request)
    oauth2_response = await authorization_server.create_token_response(oauth2_request)
    return await to_fastapi_response(oauth2_response)
