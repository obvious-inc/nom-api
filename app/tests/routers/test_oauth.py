import secrets
from typing import Callable
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.channel import Channel
from app.models.user import User
from app.schemas.apps import AppCreateSchema
from app.services.apps import create_app


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
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()
        assert "expires_in" in response.json()
        assert "token_type" in response.json()

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
    async def test_oauth2_code_flow_default_client_scopes(
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
