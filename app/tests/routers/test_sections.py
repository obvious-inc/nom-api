import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database

from app.models.server import Server
from app.models.user import User


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
