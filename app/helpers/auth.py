import logging
import time
from dataclasses import asdict, dataclass
from typing import Optional

from aioauth.collections import HTTPHeaderDict
from aioauth.config import Settings as OAuth2Settings
from aioauth.models import AuthorizationCode as OAuth2Code
from aioauth.models import Client, Token
from aioauth.requests import Post as _Post
from aioauth.requests import Query as _Query
from aioauth.requests import Request as _Request
from aioauth.server import AuthorizationServer
from aioauth.storage import BaseStorage
from aioauth.types import GrantType, RequestMethod, ResponseType, TokenType
from fastapi import Form, Query
from starlette.requests import Request

from app.config import get_settings
from app.helpers.jwt import generate_jwt_token
from app.models.app import App, AppInstalled
from app.models.auth import AuthorizationCode
from app.models.channel import Channel
from app.models.user import User
from app.schemas.apps import AppInstalledCreateSchema
from app.schemas.auth import AuthorizationCodeCreateSchema
from app.schemas.messages import AppInstallMessageCreateSchema
from app.services.apps import get_app_by_client_id
from app.services.crud import create_item, delete_item, get_item, get_item_by_id, get_items
from app.services.messages import create_app_message

logger = logging.getLogger(__name__)


@dataclass
class OAuth2Query(_Query):
    channel: Optional[str] = None


@dataclass
class OAuth2Post(_Post):
    consent: Optional[int] = 0
    channel: Optional[str] = None


@dataclass
class OAuth2Request(_Request):
    query: OAuth2Query = OAuth2Query()
    post: OAuth2Post = OAuth2Post()


async def get_oauth_settings() -> OAuth2Settings:
    settings = get_settings()
    oauth2_settings = OAuth2Settings(
        INSECURE_TRANSPORT=False if settings.environment == "production" else True,
        TOKEN_EXPIRES_IN=settings.jwt_access_token_expire_minutes * 60,
        REFRESH_TOKEN_EXPIRES_IN=settings.jwt_refresh_token_expire_minutes * 60,
    )

    return oauth2_settings


async def to_oauth2_request(request: Request, current_user: Optional[User]) -> OAuth2Request:
    oauth2_settings = await get_oauth_settings()
    form = await request.form()
    post = dict(form)
    query_params = dict(request.query_params)
    method = request.method
    headers = HTTPHeaderDict(**request.headers)
    url = str(request.url)

    return OAuth2Request(
        settings=oauth2_settings,
        method=RequestMethod[method],
        headers=headers,
        post=OAuth2Post(**post),
        query=OAuth2Query(**query_params),
        url=url,
        user=current_user,
    )


class Storage(BaseStorage):
    async def create_authorization_code(
        self,
        request: OAuth2Request,
        client_id: str,
        scope: str,
        response_type: str,
        redirect_uri: str,
        code_challenge_method: Optional[str],
        code_challenge: Optional[str],
        code: str,
    ) -> OAuth2Code:
        app: App = await get_app_by_client_id(client_id=client_id)
        if not app:
            raise Exception("App not found")

        oauth2_settings = await get_oauth_settings()
        authorization_code = OAuth2Code(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type=response_type,
            scope=scope,
            auth_time=int(time.time()),
            code_challenge_method=code_challenge_method,
            code_challenge=code_challenge,
            expires_in=oauth2_settings.AUTHORIZATION_CODE_EXPIRES_IN,
        )

        auth_code_schema = AuthorizationCodeCreateSchema(**asdict(authorization_code), app=str(app.pk))
        await create_item(
            item=auth_code_schema, result_obj=AuthorizationCode, user_field="user", current_user=request.user
        )

        return authorization_code

    async def get_authorization_code(self, request: OAuth2Request, client_id: str, code: str) -> Optional[OAuth2Code]:
        app: App = await get_app_by_client_id(client_id=client_id)
        if not app:
            return None

        auth_code_item = await get_item(
            filters={"code": code, "app": app.pk, "user": request.user},
            result_obj=AuthorizationCode,
        )

        if not auth_code_item:
            return None

        auth_code = OAuth2Code(
            code=code,
            client_id=auth_code_item.client_id,
            redirect_uri=auth_code_item.redirect_uri,
            response_type=auth_code_item.response_type,
            auth_time=auth_code_item.auth_time,
            expires_in=auth_code_item.expires_in,
            user=request.user,
            scope=auth_code_item.scope,
        )

        return auth_code

    async def get_client(
        self, request: OAuth2Request, client_id: str, client_secret: Optional[str] = None
    ) -> Optional[Client]:
        app: App = await get_app_by_client_id(client_id=client_id)
        if not app:
            return None

        return Client(
            client_id=app.client_id,
            client_secret=app.client_secret,
            redirect_uris=app.redirect_uris,
            grant_types=[GrantType.TYPE_AUTHORIZATION_CODE, GrantType.TYPE_REFRESH_TOKEN],
            response_types=[ResponseType.TYPE_CODE],
            user=app.creator,
        )

    async def delete_authorization_code(self, request: OAuth2Request, client_id: str, code: str) -> None:
        app: App = await get_app_by_client_id(client_id=client_id)
        code_item = await get_item(filters={"code": code, "app": app.pk}, result_obj=AuthorizationCode)
        if not code_item:
            raise Exception(f"Code not found: {code}")
        await delete_item(item=code_item)

    async def get_token(
        self,
        request: OAuth2Request,
        client_id: str,
        token_type: Optional[str] = TokenType.REFRESH,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> Optional[Token]:
        pass

    async def revoke_token(self, request: OAuth2Request, refresh_token: str) -> None:
        raise NotImplementedError()

    async def create_token(self, request: OAuth2Request, client_id: str, scope: str, *args) -> Token:
        app_settings = get_settings()
        app: App = await get_app_by_client_id(client_id=client_id)
        access_token = generate_jwt_token({"sub": str(app.pk), "client_id": client_id})
        refresh_token = generate_jwt_token({"sub": str(app.pk), "client_id": client_id}, token_type="refresh")

        # TODO: add caching
        # await cache.client.sadd(f"refresh_tokens:{str(app.pk)}", refresh_token)
        # await create_item(
        #     RefreshTokenCreateSchema(refresh_token=refresh_token, app=str(app.pk)),
        #     result_obj=RefreshToken,
        #     user_field="app",
        #     current_user=app,
        # )

        channel_id = request.post.channel
        if not channel_id:
            raise Exception("missing channel_id")

        channel = await get_item_by_id(id_=channel_id, result_obj=Channel)

        prev_installed_apps = await get_items(filters={"app": app.pk, "channel": channel.pk}, result_obj=AppInstalled)

        if not prev_installed_apps:
            # TODO: at this stage, the app has been verified and will be installed into the channel/server
            install_model = AppInstalledCreateSchema(app=str(app.pk), channel=str(channel.pk))
            new_install = await create_item(item=install_model, current_user=request.user, result_obj=AppInstalled)

            logger.debug("New app installed: %s", new_install)
            message = AppInstallMessageCreateSchema(
                channel=channel_id, app=str(app.pk), installer=str(request.user.pk), type=6
            )
            await create_app_message(message_model=message)

        token = Token(
            client_id=client_id,
            expires_in=app_settings.jwt_access_token_expire_minutes,
            refresh_token_expires_in=app_settings.jwt_refresh_token_expire_minutes,
            access_token=access_token,
            refresh_token=refresh_token,
            issued_at=int(time.time()),
            scope=scope,
            revoked=False,
        )
        return token


class OAuth2CodeAuthorizationRequestForm:
    def __init__(
        self,
        response_type: str = Query(None, regex="code"),
        client_id: Optional[str] = Query(None),
        redirect_uri: Optional[str] = Query(None),
        scope: str = Query(""),
        state: Optional[str] = Query(None),
    ):
        self.response_type = response_type
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.scopes = scope.split()
        self.state = state


class OAuth2CodeTokenRequestForm:
    def __init__(
        self,
        code: str = Form(None),
        grant_type: str = Form(None, regex="code"),
        redirect_uri: Optional[str] = Form(None),
        client_id: Optional[str] = Form(None),
        client_secret: Optional[str] = Form(None),
    ):
        self.code = code
        self.grant_type = grant_type
        self.redirect_uri = redirect_uri
        self.client_id = client_id
        self.client_secret = client_secret


storage = Storage()
authorization_server = AuthorizationServer(storage=storage)
