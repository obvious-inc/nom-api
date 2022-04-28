import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.server import Server
from app.models.user import User
from app.schemas.channels import ServerChannelCreateSchema
from app.services.channels import create_server_channel


class TestSectionRoutes:
    @pytest.mark.asyncio
    async def test_update_section_name(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        new_section_data = {"name": "community"}
        response = await authorized_client.post(f"/servers/{str(server.pk)}/sections", json=new_section_data)
        assert response.status_code == 201
        json_resp = response.json()
        section_id = json_resp["id"]
        assert json_resp["name"] == new_section_data["name"]

        data = {"name": "new-community"}
        response = await authorized_client.patch(f"/sections/{section_id}", json=data)
        assert response.status_code == 200
        json_resp = response.json()
        assert json_resp["name"] == data["name"]

    @pytest.mark.asyncio
    async def test_update_section_channels(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        new_section_data = {"name": "community"}
        response = await authorized_client.post(f"/servers/{str(server.pk)}/sections", json=new_section_data)
        assert response.status_code == 201
        json_resp = response.json()
        section_id = json_resp["id"]
        assert json_resp["name"] == new_section_data["name"]
        assert json_resp["channels"] == []

        ch_names = ["gm", "offtopic"]
        channels = []
        for channel_name in ch_names:
            channel = await create_server_channel(
                ServerChannelCreateSchema(kind="server", server=str(server.id), name=channel_name),
                current_user=current_user,
            )
            channels.append(channel)

        data = {"channels": [str(channel.pk) for channel in channels]}
        response = await authorized_client.patch(f"/sections/{section_id}", json=data)
        assert response.status_code == 200
        json_resp = response.json()
        assert json_resp["channels"] != []
        assert len(json_resp["channels"]) == len(ch_names)
        assert json_resp["channels"] == data["channels"]

    @pytest.mark.asyncio
    async def test_update_section_channels_order_matters(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        new_section_data = {"name": "community"}
        response = await authorized_client.post(f"/servers/{str(server.pk)}/sections", json=new_section_data)
        assert response.status_code == 201
        json_resp = response.json()
        section_id = json_resp["id"]

        ch_names = ["gm", "offtopic"]
        channels = []
        for channel_name in ch_names:
            channel = await create_server_channel(
                ServerChannelCreateSchema(kind="server", server=str(server.id), name=channel_name),
                current_user=current_user,
            )
            channels.append(channel)

        data = {"channels": [str(channel.pk) for channel in reversed(channels)]}
        response = await authorized_client.patch(f"/sections/{section_id}", json=data)
        assert response.status_code == 200
        json_resp = response.json()
        assert json_resp["channels"] != []
        assert len(json_resp["channels"]) == len(ch_names)
        assert json_resp["channels"] == data["channels"]

    @pytest.mark.asyncio
    async def test_delete_section(
        self, app: FastAPI, db: Database, current_user: User, authorized_client: AsyncClient, server: Server
    ):
        new_section_data = {"name": "community"}
        response = await authorized_client.post(f"/servers/{str(server.pk)}/sections", json=new_section_data)
        assert response.status_code == 201
        section = response.json()

        response = await authorized_client.get(f"/servers/{str(server.pk)}/sections")
        assert response.status_code == 200
        resp_sections = response.json()
        assert len(resp_sections) == 1

        response = await authorized_client.delete(f"/sections/{section['id']}")
        assert response.status_code == 204

        response = await authorized_client.get(f"/servers/{str(server.pk)}/sections")
        assert response.status_code == 200
        resp_sections = response.json()
        assert len(resp_sections) == 0
