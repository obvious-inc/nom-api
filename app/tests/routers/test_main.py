import pytest
from fastapi import FastAPI
from httpx import AsyncClient


@pytest.mark.asyncio
class TestMainRoutes:

    async def test_api_status(self, app: FastAPI, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
