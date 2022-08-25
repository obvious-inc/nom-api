import asyncio
import secrets
from typing import Callable
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.config import get_settings
from app.helpers.auth import get_oauth_settings
from app.models.auth import AuthorizationCode
from app.models.channel import Channel
from app.models.user import User
from app.schemas.apps import AppCreateSchema
from app.services.apps import create_app
from app.services.crud import get_item


class TestOAuthRoutes:
    @pytest.mark.asyncio
    async def test_oauth2_code_flow_ok(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com"
        state = secrets.token_urlsafe(32)

        app_schema = AppCreateSchema(name="test", redirect_uris=[redirect_uri])
        integration = await create_app(model=app_schema, current_user=current_user)
        assert integration is not None

        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": "",
            "response_type": "code",
            "channel": str(topic_channel.pk),
            "state": state,
        }

        form_data = {"consent": 1}
        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 200
        json_resp = response.json()
        location = json_resp.get("location")
        url = urlparse(location)
        assert f"{url.scheme}://{url.netloc}" == redirect_uri

        url_params: dict = parse_qs(url.query)
        code = url_params.get("code")
        assert code is not None
        assert code != ""

        redirect_state = url_params.get("state", [])[0]
        assert redirect_state is not None
        assert redirect_state != ""
        assert redirect_state == state

        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 200
        json_resp = response.json()
        assert "access_token" in json_resp
        assert "refresh_token" in json_resp
        assert "expires_in" in json_resp
        assert "token_type" in json_resp

    @pytest.mark.asyncio
    async def test_oauth2_code_flow_missing_channel(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        get_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com"
        app_schema = AppCreateSchema(name="test", redirect_uris=[redirect_uri])
        integration = await create_app(model=app_schema, current_user=current_user)
        assert integration is not None

        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": "",
            "response_type": "code",
        }

        form_data = {"consent": 1}
        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 400
        assert "Missing channel" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_oauth2_code_flow_no_consent(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com"
        state = secrets.token_urlsafe(32)

        app_schema = AppCreateSchema(name="test", redirect_uris=[redirect_uri])
        integration = await create_app(model=app_schema, current_user=current_user)
        assert integration is not None

        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": "",
            "response_type": "code",
            "channel": str(topic_channel.pk),
            "state": state,
        }

        form_data = {"consent": 0}
        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 400
        assert "Consent not granted" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_oauth2_code_flow_guest_in_topic_channel_nok(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
        guest_user: User,
    ):
        redirect_uri = "https://example.com"
        state = secrets.token_urlsafe(32)

        app_schema = AppCreateSchema(name="test", redirect_uris=[redirect_uri])
        integration = await create_app(model=app_schema, current_user=current_user)
        assert integration is not None

        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": "",
            "response_type": "code",
            "channel": str(topic_channel.pk),
            "state": state,
        }

        form_data = {"consent": 1}
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_oauth2_code_flow_unauth_scopes(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com"
        state = secrets.token_urlsafe(32)
        app_scopes = ["messages.list", "channels.view"]
        auth_scopes = ["messages.list", "messages.create"]

        app_schema = AppCreateSchema(name="test", redirect_uris=[redirect_uri], scopes=app_scopes)
        integration = await create_app(model=app_schema, current_user=current_user)
        assert integration is not None

        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(auth_scopes),
            "response_type": "code",
            "channel": str(topic_channel.pk),
            "state": state,
        }

        form_data = {"consent": 1}
        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 400
        assert "invalid_scope" in response.json()["error"]

    @pytest.mark.asyncio
    async def test_oauth2_code_flow_scopes_ok(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com"
        state = secrets.token_urlsafe(32)
        app_scopes = ["messages.list", "messages.create"]
        auth_scopes = ["messages.list"]

        app_schema = AppCreateSchema(name="test", redirect_uris=[redirect_uri], scopes=app_scopes)
        integration = await create_app(model=app_schema, current_user=current_user)
        assert integration is not None

        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(auth_scopes),
            "response_type": "code",
            "channel": str(topic_channel.pk),
            "state": state,
        }

        form_data = {"consent": 1}
        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 200
        json_resp = response.json()
        location = json_resp.get("location")
        url = urlparse(location)
        assert f"{url.scheme}://{url.netloc}" == redirect_uri

        url_params: dict = parse_qs(url.query)
        code = url_params.get("code")
        assert code is not None
        assert code != ""

        redirect_state = url_params.get("state", [])[0]
        assert redirect_state is not None
        assert redirect_state != ""
        assert redirect_state == state

        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 200
        json_resp = response.json()
        assert "access_token" in json_resp
        assert "refresh_token" in json_resp
        assert "expires_in" in json_resp
        assert "token_type" in json_resp
        assert "scope" in json_resp
        assert json_resp["scope"] == " ".join(auth_scopes)

    @pytest.mark.asyncio
    async def test_oauth2_code_flow_default_client_scopes_nok(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com"
        state = secrets.token_urlsafe(32)
        app_scopes = ["messages.list", "messages.create"]

        app_schema = AppCreateSchema(name="test", redirect_uris=[redirect_uri], scopes=app_scopes)
        integration = await create_app(model=app_schema, current_user=current_user)
        assert integration is not None

        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "channel": str(topic_channel.pk),
            "state": state,
        }

        form_data = {"consent": 1}
        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 200
        json_resp = response.json()
        location = json_resp.get("location")
        url = urlparse(location)
        assert f"{url.scheme}://{url.netloc}" == redirect_uri

        url_params: dict = parse_qs(url.query)
        code = url_params.get("code")
        assert code is not None
        assert code != ""

        redirect_state = url_params.get("state", [])[0]
        assert redirect_state is not None
        assert redirect_state != ""
        assert redirect_state == state

        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 200
        json_resp = response.json()
        assert "access_token" in json_resp
        assert "refresh_token" in json_resp
        assert "expires_in" in json_resp
        assert "token_type" in json_resp
        assert "scope" in json_resp
        assert json_resp["scope"] == " ".join(app_scopes)

    @pytest.mark.asyncio
    async def test_oauth2_code_flow_scope_unknown(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com"
        state = secrets.token_urlsafe(32)
        app_scopes = ["messages.list", "messages.create"]
        auth_scopes = ["some.stuff"]

        app_schema = AppCreateSchema(name="test", redirect_uris=[redirect_uri], scopes=app_scopes)
        integration = await create_app(model=app_schema, current_user=current_user)
        assert integration is not None

        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(auth_scopes),
            "response_type": "code",
            "channel": str(topic_channel.pk),
            "state": state,
        }

        form_data = {"consent": 1}
        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_oauth2_code_flow_missing_code(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com"
        app_schema = AppCreateSchema(name="test", redirect_uris=[redirect_uri])
        integration = await create_app(model=app_schema, current_user=current_user)
        assert integration is not None

        data = {
            "code": "random-code",
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_oauth2_app_requests(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
        get_app_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com"
        app_schema = AppCreateSchema(name="Snapshot", redirect_uris=[redirect_uri], scopes=["messages.list"])
        integration = await create_app(model=app_schema, current_user=current_user)

        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": "messages.list",
            "response_type": "code",
            "channel": str(topic_channel.pk),
        }

        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data={"consent": 1})
        assert response.status_code == 200
        json_resp = response.json()
        location = json_resp.get("location")
        url = urlparse(location)
        assert f"{url.scheme}://{url.netloc}" == redirect_uri

        url_params: dict = parse_qs(url.query)
        code = url_params.get("code")
        assert code is not None
        assert code != ""

        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 200
        access_token = response.json().get("access_token")
        refresh_token = response.json().get("refresh_token")

        app_client = await get_app_authorized_client(
            integration, access_token=access_token, refresh_token=refresh_token
        )
        response = await app_client.get(f"/channels/{str(topic_channel.pk)}/messages")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_oauth2_refresh_token(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com"
        app_schema = AppCreateSchema(name="Snapshot", redirect_uris=[redirect_uri], scopes=["messages.list"])
        integration = await create_app(model=app_schema, current_user=current_user)

        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": "messages.list",
            "response_type": "code",
            "channel": str(topic_channel.pk),
        }

        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data={"consent": 1})
        assert response.status_code == 200
        json_resp = response.json()
        location = json_resp.get("location")
        url = urlparse(location)
        assert f"{url.scheme}://{url.netloc}" == redirect_uri

        params = parse_qs(url.query)
        code = params.get("code")
        assert code is not None
        assert code != ""

        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 200
        refresh_token = response.json().get("refresh_token")

        data = {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }
        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 200
        json_resp = response.json()
        assert "access_token" in json_resp
        assert "refresh_token" in json_resp

    @pytest.mark.asyncio
    async def test_oauth2_access_token_expiry(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
        monkeypatch,
        get_app_authorized_client: Callable,
    ):
        get_settings.cache_clear()
        monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "0")
        current_settings = await get_oauth_settings()
        assert current_settings.TOKEN_EXPIRES_IN < 1

        redirect_uri = "https://example.com"
        state = secrets.token_urlsafe(32)

        app_schema = AppCreateSchema(name="test", redirect_uris=[redirect_uri])
        integration = await create_app(model=app_schema, current_user=current_user)
        assert integration is not None

        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": "",
            "response_type": "code",
            "channel": str(topic_channel.pk),
            "state": state,
        }

        form_data = {"consent": 1}
        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 200
        json_resp = response.json()
        location = json_resp.get("location")
        url = urlparse(location)
        assert f"{url.scheme}://{url.netloc}" == redirect_uri

        url_params: dict = parse_qs(url.query)
        code = url_params.get("code")
        assert code is not None
        assert code != ""

        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        access_token = response.json()["access_token"]
        refresh_token = response.json()["refresh_token"]

        app_client = await get_app_authorized_client(
            integration, channels=[topic_channel], access_token=access_token, refresh_token=refresh_token
        )

        await asyncio.sleep(1)

        data = {"content": "gm!", "channel": str(topic_channel.pk)}
        response = await app_client.post("/messages", json=data)
        assert response.status_code == 401
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_oauth2_refresh_token_expiry(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
        monkeypatch,
    ):
        get_settings.cache_clear()
        monkeypatch.setenv("JWT_REFRESH_TOKEN_EXPIRE_MINUTES", "0")
        current_settings = await get_oauth_settings()
        assert current_settings.REFRESH_TOKEN_EXPIRES_IN < 1

        redirect_uri = "https://example.com"
        app_schema = AppCreateSchema(name="Snapshot", redirect_uris=[redirect_uri], scopes=["messages.list"])
        integration = await create_app(model=app_schema, current_user=current_user)

        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": "messages.list",
            "response_type": "code",
            "channel": str(topic_channel.pk),
        }

        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data={"consent": 1})
        assert response.status_code == 200
        json_resp = response.json()
        location = json_resp.get("location")
        url = urlparse(location)
        assert f"{url.scheme}://{url.netloc}" == redirect_uri

        params = parse_qs(url.query)
        code = params.get("code")
        assert code is not None
        assert code != ""

        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 200
        refresh_token = response.json().get("refresh_token")

        data = {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }
        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 400
        json_response = response.json()
        assert json_response["error"] == "invalid_grant"
        get_settings.cache_clear()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "app_redirect_uris, request_redirect_uri",
        [
            (
                ["https://example.com/newshades/callback"],
                "https://example.com",
            ),
            (
                ["https://example.com/newshades/callback"],
                "https://example.com/newshades/callback &@foo.evil-user.net#@bar.evil-user.net/",
            ),
            (
                ["https://example.com/newshades/callback", "https://newshades.xyz"],
                "https://newshades.xyz.hack-it.com",
            ),
        ],
    )
    async def test_oauth2_code_flow_invalid_redirect_uris(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
        app_redirect_uris,
        request_redirect_uri,
    ):
        app_schema = AppCreateSchema(name="test", redirect_uris=app_redirect_uris)
        integration = await create_app(model=app_schema, current_user=current_user)

        params = {
            "client_id": integration.client_id,
            "scope": "",
            "response_type": "code",
            "channel": str(topic_channel.pk),
            "redirect_uri": request_redirect_uri,
        }

        form_data = {"consent": 1}
        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 400
        assert "invalid redirect uri" in response.json().get("description").lower()

    @pytest.mark.asyncio
    async def test_oauth2_code_flow_double_redirect_uris(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
    ):
        app_schema = AppCreateSchema(name="test", redirect_uris=["https://example.com/callback"])
        integration = await create_app(model=app_schema, current_user=current_user)

        params = {
            "client_id": integration.client_id,
            "scope": "",
            "response_type": "code",
            "channel": str(topic_channel.pk),
            "redirect_uri": ["https://example.com/callback", "https://my-hack-site.com/callback"],
        }

        form_data = {"consent": 1}
        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 400
        assert "invalid redirect uri" in response.json().get("description").lower()

    @pytest.mark.asyncio
    async def test_oauth2_code_flow_double_redirect_uris_2(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com/callback"
        app_schema = AppCreateSchema(name="test", redirect_uris=[redirect_uri])
        integration = await create_app(model=app_schema, current_user=current_user)

        params = {
            "client_id": integration.client_id,
            "scope": "",
            "response_type": "code",
            "channel": str(topic_channel.pk),
            "redirect_uri": ["https://my-hack-site.com/callback", redirect_uri],
        }

        form_data = {"consent": 1}
        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 200
        json_resp = response.json()

        location = json_resp.get("location")
        url = urlparse(location)
        assert f"{url.scheme}://{url.netloc}{url.path}" == redirect_uri

        url_params: dict = parse_qs(url.query)
        code = url_params.get("code", [])[0]
        assert code is not None

        code_item = await get_item(filters={"code": code, "app": integration.pk}, result_obj=AuthorizationCode)
        assert code_item is not None
        assert code_item.redirect_uri == redirect_uri

    @pytest.mark.asyncio
    async def test_oauth2_code_flow_scopes_upgrade_nok(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com"
        state = secrets.token_urlsafe(32)
        app_scopes = ["messages.list", "messages.create"]
        auth_scopes = ["messages.list"]

        app_schema = AppCreateSchema(name="test", redirect_uris=[redirect_uri], scopes=app_scopes)
        integration = await create_app(model=app_schema, current_user=current_user)

        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(auth_scopes),
            "response_type": "code",
            "channel": str(topic_channel.pk),
            "state": state,
        }

        form_data = {"consent": 1}
        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 200
        json_resp = response.json()
        location = json_resp.get("location")
        url = urlparse(location)
        assert f"{url.scheme}://{url.netloc}" == redirect_uri

        url_params: dict = parse_qs(url.query)
        code = url_params.get("code")
        assert code is not None
        assert code != ""

        redirect_state = url_params.get("state", [])[0]
        assert redirect_state is not None
        assert redirect_state != ""
        assert redirect_state == state

        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        token_scopes = ["messages.list", "messages.create"]
        data["scope"] = " ".join(token_scopes)

        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 400
        json_resp = response.json()
        assert json_resp.get("error") == "invalid_scope"

    @pytest.mark.asyncio
    async def test_oauth2_refresh_token_upgrade_scope_nok(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com"
        app_scopes = ["messages.list", "messages.create"]
        app_schema = AppCreateSchema(name="Snapshot", redirect_uris=[redirect_uri], scopes=app_scopes)
        integration = await create_app(model=app_schema, current_user=current_user)

        original_auth_code_scopes = ["messages.list"]
        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(original_auth_code_scopes),
            "response_type": "code",
            "channel": str(topic_channel.pk),
        }

        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data={"consent": 1})
        assert response.status_code == 200
        json_resp = response.json()
        location = json_resp.get("location")
        url = urlparse(location)
        assert f"{url.scheme}://{url.netloc}" == redirect_uri

        params = parse_qs(url.query)
        code = params.get("code")
        assert code is not None
        assert code != ""

        data = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 200
        refresh_token = response.json().get("refresh_token")

        refresh_scopes = original_auth_code_scopes.copy()
        refresh_scopes.append("messages.create")

        data = {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
            "scope": " ".join(refresh_scopes),
        }
        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 200
        json_resp = response.json()
        assert "access_token" in json_resp
        assert "refresh_token" in json_resp
        assert "scope" in json_resp
        assert json_resp.get("scope") == " ".join(original_auth_code_scopes)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "grant_type",
        ["password", "client_credentials"],
    )
    async def test_oauth2_post_token_not_implemented_grant_types(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
        grant_type,
    ):
        redirect_uri = "https://example.com"
        app_scopes = ["messages.list", "messages.create"]
        app_schema = AppCreateSchema(name="Snapshot", redirect_uris=[redirect_uri], scopes=app_scopes)
        integration = await create_app(model=app_schema, current_user=current_user)

        auth_scopes = ["messages.list"]
        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(auth_scopes),
            "response_type": "code",
            "channel": str(topic_channel.pk),
        }

        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data={"consent": 1})
        assert response.status_code == 200
        json_resp = response.json()
        location = json_resp.get("location")
        url = urlparse(location)
        assert f"{url.scheme}://{url.netloc}" == redirect_uri

        params = parse_qs(url.query)
        code = params.get("code")
        assert code is not None
        assert code != ""

        data = {
            "code": code,
            "grant_type": grant_type,
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 400
        assert response.json().get("error", "") == "unauthorized_client"

    @pytest.mark.asyncio
    async def test_oauth2_post_token_not_supported_grant_types(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        topic_channel: Channel,
        get_authorized_client: Callable,
    ):
        redirect_uri = "https://example.com"
        app_scopes = ["messages.list", "messages.create"]
        app_schema = AppCreateSchema(name="Snapshot", redirect_uris=[redirect_uri], scopes=app_scopes)
        integration = await create_app(model=app_schema, current_user=current_user)

        auth_scopes = ["messages.list"]
        params = {
            "client_id": integration.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(auth_scopes),
            "response_type": "code",
            "channel": str(topic_channel.pk),
        }

        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data={"consent": 1})
        assert response.status_code == 200
        json_resp = response.json()
        location = json_resp.get("location")
        url = urlparse(location)
        assert f"{url.scheme}://{url.netloc}" == redirect_uri

        params = parse_qs(url.query)
        code = params.get("code")
        assert code is not None
        assert code != ""

        data = {
            "code": code,
            "grant_type": "token",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        response = await user_auth_client.post(
            "/oauth/token", data=data, auth=(integration.client_id, integration.client_secret)
        )
        assert response.status_code == 400
        assert response.json().get("error", "") == "unsupported_grant_type"
