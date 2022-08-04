import time
from typing import Optional

from aioauth.config import Settings
from aioauth.models import AuthorizationCode, Client, Token
from aioauth.requests import Request
from aioauth.server import AuthorizationServer
from aioauth.storage import BaseStorage
from aioauth.types import GrantType, ResponseType, TokenType
from fastapi import Form, Query

from app.config import get_settings
from app.helpers.jwt import generate_jwt_token
from app.models.app import App
from app.models.user import User
from app.services.apps import get_app_by_client_id
from app.services.crud import get_item


class Storage(BaseStorage):
    """
    Storage methods must be implemented here.
    """

    async def get_token(
        self,
        request: Request,
        client_id: str,
        token_type: Optional[str] = TokenType.REFRESH,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> Optional[Token]:
        pass

    async def authenticate(self, request: Request) -> bool:
        pass

    async def revoke_token(self, request: Request, refresh_token: str) -> None:
        pass

    async def get_client(
        self, request: Request, client_id: str, client_secret: Optional[str] = None
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

    async def get_authorization_code(self, request: Request, client_id: str, code: str) -> Optional[AuthorizationCode]:
        # TODO: fix this
        default_user = await get_item(filters={}, result_obj=User)
        app: App = await get_app_by_client_id(client_id=client_id)
        if not app:
            return None

        auth_code = AuthorizationCode(
            code=code,
            client_id=client_id,
            redirect_uri=request.query.redirect_uri,
            response_type=ResponseType.TYPE_CODE,
            auth_time=int(time.time()) - 5,
            expires_in=300,
            user=default_user,
            scope=request.query.scope,
        )
        return auth_code

    async def delete_authorization_code(self, request: Request, client_id: str, code: str) -> None:
        # TODO: delete codes...
        return

    async def create_token(self, request: Request, client_id: str, scope: str, *args) -> Token:
        app_settings = get_settings()
        app: App = await get_app_by_client_id(client_id=client_id)
        access_token = generate_jwt_token({"sub": str(app.pk), "client_id": client_id})
        refresh_token = generate_jwt_token({"sub": str(app.pk)}, token_type="refresh")

        # TODO: add caching
        # await cache.client.sadd(f"refresh_tokens:{str(app.pk)}", refresh_token)
        # await create_item(
        #     RefreshTokenCreateSchema(refresh_token=refresh_token, app=str(app.pk)),
        #     result_obj=RefreshToken,
        #     user_field="app",
        #     current_user=app,
        # )

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


# TODO: fix this properly
settings = Settings(INSECURE_TRANSPORT=True)

storage = Storage()
authorization_server = AuthorizationServer(storage)
