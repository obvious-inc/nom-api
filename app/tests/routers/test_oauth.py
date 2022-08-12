import secrets
from typing import Callable

import pytest
from fastapi import FastAPI
from httpx import URL, AsyncClient
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

        response = await client.get("/oauth/authorize", params=params, follow_redirects=False)
        assert response.status_code == 307

        form_data = {"consent": 1}
        user_auth_client = await get_authorized_client(current_user)
        response = await user_auth_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 200
        url: URL = response.url
        assert f"{url.scheme}://{url.netloc.decode('ascii')}" == redirect_uri

        code = url.params.get("code")
        assert code is not None
        assert code != ""

        redirect_state = url.params.get("state")
        assert redirect_state is not None
        assert redirect_state != ""
        assert redirect_state == state

        data = {
            "code": code,
            "client_id": integration.client_id,
            "client_secret": integration.client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        response = await user_auth_client.post("/oauth/token", data=data)
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

        response = await client.get("/oauth/authorize", params=params, follow_redirects=False)
        assert response.status_code == 307

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

        response = await client.get("/oauth/authorize", params=params, follow_redirects=False)
        assert response.status_code == 307

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

        response = await client.get("/oauth/authorize", params=params, follow_redirects=False)
        assert response.status_code == 307

        form_data = {"consent": 1}
        guest_client = await get_authorized_client(guest_user)
        response = await guest_client.post("/oauth/authorize", params=params, data=form_data)
        assert response.status_code == 403

        data = {
            "code": "123123",
            "client_id": integration.client_id,
            "client_secret": integration.client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "channel": str(topic_channel.pk),
        }

        response = await guest_client.post("/oauth/token", data=data)
        assert response.status_code == 403
