import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Literal, Optional, cast

from aioauth.collections import HTTPHeaderDict
from aioauth.config import Settings as OAuth2Settings
from aioauth.errors import InvalidScopeError
from aioauth.models import AuthorizationCode as OAuth2Code
from aioauth.models import Client, Token
from aioauth.requests import BaseRequest
from aioauth.requests import Post as _Post
from aioauth.requests import Query as _Query
from aioauth.requests import TRequest
from aioauth.responses import Response as OAuth2Response
from aioauth.server import AuthorizationServer
from aioauth.storage import BaseStorage
from aioauth.types import CodeChallengeMethod
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings
from app.helpers.cache_utils import cache
from app.helpers.jwt import generate_jwt_token
from app.helpers.permissions import validate_oauth_request_scope_str
from app.models.app import App, AppInstalled
from app.models.auth import AuthorizationCode, RefreshToken
from app.models.user import User
from app.schemas.apps import AppInstalledCreateSchema
from app.schemas.auth import AuthorizationCodeCreateSchema, RefreshTokenCreateSchema
from app.schemas.messages import AppInstallMessageCreateSchema
from app.services.apps import get_app_by_client_id
from app.services.crud import create_item, delete_item, get_item, update_item
from app.services.messages import create_app_message

logger = logging.getLogger(__name__)


@dataclass
class OAuth2Query(_Query):
    channel: Optional[str] = None


@dataclass
class OAuth2Post(_Post):
    consent: Optional[str] = "0"
    channel: Optional[str] = None


@dataclass
class OAuth2Request(BaseRequest[OAuth2Query, OAuth2Post, Any]):
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


async def to_fastapi_response(oauth2_response: OAuth2Response) -> Response:
    response_content = oauth2_response.content
    headers = dict(oauth2_response.headers)
    status_code = oauth2_response.status_code
    content = json.dumps(response_content)

    return Response(content=content, headers=headers, status_code=status_code)


async def to_oauth2_request(request: Request, current_user: Optional[User] = None) -> OAuth2Request:
    oauth2_settings = await get_oauth_settings()
    form = await request.form()
    post: OAuth2Post = OAuth2Post(**form)

    query_params = request.query_params
    query: OAuth2Query = OAuth2Query(**query_params)
    method = cast(Literal["GET", "POST"], request.method)
    headers = HTTPHeaderDict(**request.headers)
    url = str(request.url)

    return OAuth2Request(
        settings=oauth2_settings,
        method=method,
        headers=headers,
        post=post,
        query=query,
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
        code_challenge_method: Optional[CodeChallengeMethod],
        code_challenge: Optional[str],
        code: str,
    ) -> OAuth2Code:
        app: App = await get_app_by_client_id(client_id=client_id)

        if not scope:
            scope = " ".join(app.scopes)

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

        auth_code_schema = AuthorizationCodeCreateSchema(
            **asdict(authorization_code), app=str(app.pk), channel=request.query.channel
        )
        await create_item(
            item=auth_code_schema, result_obj=AuthorizationCode, user_field="user", current_user=request.user
        )

        return authorization_code

    async def get_authorization_code(self, request: OAuth2Request, client_id: str, code: str) -> Optional[OAuth2Code]:
        app: App = await get_app_by_client_id(client_id=client_id)
        auth_code_item = await get_item(filters={"code": code, "app": app.pk}, result_obj=AuthorizationCode)
        if not auth_code_item:
            return None

        auth_code = OAuth2Code(
            code=code,
            client_id=auth_code_item.client_id,
            redirect_uri=auth_code_item.redirect_uri,
            response_type=auth_code_item.response_type,
            auth_time=auth_code_item.auth_time,
            expires_in=auth_code_item.expires_in,
            user=auth_code_item.user,
            scope=auth_code_item.scope,
        )

        return auth_code

    async def get_client(
        self, request: OAuth2Request, client_id: str, client_secret: Optional[str] = None
    ) -> Optional[Client]:
        app: App = await get_app_by_client_id(client_id=client_id)
        if not app:
            return None

        if client_secret and app.client_secret != client_secret:
            return None

        client = Client(
            client_id=app.client_id,
            client_secret=app.client_secret,
            redirect_uris=app.redirect_uris,
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            user=app.creator,
            scope=" ".join(app.scopes),
        )

        return client

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
        token_type: Optional[str] = "refresh_token",
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> Optional[Token]:
        oauth_settings = await get_oauth_settings()
        app: App = await get_app_by_client_id(client_id=client_id)

        r_token = await get_item(filters={"refresh_token": refresh_token, "app": app.pk}, result_obj=RefreshToken)
        if r_token is None:
            return None

        token = Token(
            client_id=client_id,
            expires_in=oauth_settings.TOKEN_EXPIRES_IN,
            refresh_token_expires_in=oauth_settings.REFRESH_TOKEN_EXPIRES_IN,
            access_token="",
            refresh_token=r_token.refresh_token,
            issued_at=int(r_token.created_at.timestamp()),
            scope=" ".join(r_token.scopes),
            revoked=r_token.used or r_token.deleted,
        )
        return token

    async def revoke_token(self, request: OAuth2Request, refresh_token: str) -> None:
        r_token = await get_item(filters={"refresh_token": refresh_token}, result_obj=RefreshToken)
        if not r_token:
            raise Exception("refresh token not found")
        await delete_item(r_token)

    async def create_token(self, request: OAuth2Request, client_id: str, scope: str, *args) -> Token:
        app_settings = get_settings()
        app: App = await get_app_by_client_id(client_id=client_id)

        if request.post.grant_type == "authorization_code":
            code = request.post.code
            code_item = await get_item(filters={"code": code, "app": app.pk}, result_obj=AuthorizationCode)
            if not code_item:
                raise Exception("code not found")

            # for access tokens, scope should be the same as the issued code
            code_scope = code_item.scope
            if scope and scope != code_scope:
                logger.error(f"upgrading scope not allowed. expected: {code_scope} | request: {scope}")
                raise InvalidScopeError[TRequest](request=request)

            scopes = await validate_oauth_request_scope_str(scope=code_scope)

            channel = await code_item.channel.fetch()
            channel_id = str(channel.pk)
            if not channel:
                raise Exception("missing channel_id")

            if not request.user:
                request.user = code_item.user

            prev_installed_app = await get_item(filters={"app": app.pk, "channel": channel.pk}, result_obj=AppInstalled)

            if not prev_installed_app:
                if not request.user:
                    raise Exception("User not found in request")

                install_model = AppInstalledCreateSchema(app=str(app.pk), channel=str(channel.pk), scopes=scopes)
                await create_item(item=install_model, current_user=request.user, result_obj=AppInstalled)

                message = AppInstallMessageCreateSchema(
                    channel=channel_id, app=str(app.pk), installer=str(request.user.pk), type=6
                )
                await create_app_message(message_model=message)
            else:
                existing_scopes = prev_installed_app.scopes
                final_scopes = list(set(existing_scopes) | set(scopes))
                await update_item(prev_installed_app, {"scopes": final_scopes})
                await cache.client.hset(f"app:{str(app.pk)}", f"channel:{channel_id}", ",".join(final_scopes))

        elif request.post.grant_type == "refresh_token":
            scopes = await validate_oauth_request_scope_str(scope=scope)
        else:
            raise Exception("unexpected grant type", request.post.grant_type)

        access_token = generate_jwt_token({"sub": str(app.pk), "client_id": client_id, "scopes": scopes})
        refresh_token = generate_jwt_token(
            {"sub": str(app.pk), "client_id": client_id, "scopes": scopes}, token_type="refresh"
        )

        await cache.client.sadd(f"refresh_tokens:{str(app.pk)}", refresh_token)
        await create_item(
            RefreshTokenCreateSchema(refresh_token=refresh_token, app=str(app.pk), scopes=scopes),
            result_obj=RefreshToken,
            user_field=None,
        )

        token = Token(
            client_id=client_id,
            expires_in=app_settings.jwt_access_token_expire_minutes,
            refresh_token_expires_in=app_settings.jwt_refresh_token_expire_minutes,
            access_token=access_token,
            refresh_token=refresh_token,
            issued_at=int(time.time()),
            scope=" ".join(scopes),
            revoked=False,
        )
        return token


storage = Storage()
authorization_server: AuthorizationServer = AuthorizationServer(storage=storage)
