import logging

from aioauth.collections import HTTPHeaderDict
from aioauth.config import Settings
from aioauth.requests import Post
from aioauth.requests import Query as OAuth2Query
from aioauth.requests import Request as OAuth2Request
from aioauth.types import RequestMethod
from aioauth_fastapi.utils import to_fastapi_response
from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.helpers.auth import authorization_server
from app.models.user import User
from app.services.crud import get_item

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/authorize")
@router.post("/authorize")
async def get_app_authorization_page(request: Request):
    # TODO: only diff between aioauth router and ours is the user. maybe add user to request and use theirs?

    # TODO: sort out redirection between GET and POST
    # if request.method == "GET":
    #     url = "http://localhost:8080/oauth/authorize"
    #     return RedirectResponse(url)

    form = await request.form()
    post = dict(form)
    query_params = dict(request.query_params)
    headers = HTTPHeaderDict(**request.headers)
    url = str(request.url)
    settings = Settings(INSECURE_TRANSPORT=True)
    default_user = await get_item(filters={}, result_obj=User)
    oauth2_request = OAuth2Request(
        settings=settings,
        method=RequestMethod[request.method],
        headers=headers,
        post=Post(**post),
        query=OAuth2Query(**query_params),
        url=url,
        user=default_user,
    )

    oauth2_response = await authorization_server.create_authorization_response(oauth2_request)
    return await to_fastapi_response(oauth2_response)


@router.post("/token")
async def create_access_token(request: Request):
    form = await request.form()
    post = dict(form)
    query_params = dict(request.query_params)
    headers = HTTPHeaderDict(**request.headers)
    url = str(request.url)
    settings = Settings(INSECURE_TRANSPORT=True)
    default_user = await get_item(filters={}, result_obj=User)
    oauth2_request = OAuth2Request(
        settings=settings,
        method=RequestMethod[request.method],
        headers=headers,
        post=Post(**post),
        query=OAuth2Query(**query_params),
        url=url,
        user=default_user,
    )
    oauth2_response = await authorization_server.create_token_response(oauth2_request)
    return await to_fastapi_response(oauth2_response)
