import pytest
from bson import ObjectId
from fastapi import FastAPI
from httpx import AsyncClient

from app.models.channel import Channel


class TestDependenciesRouter:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "query_params",
        [
            {"before": str(ObjectId()), "after": str(ObjectId())},
            {"before": str(ObjectId()), "around": str(ObjectId())},
            {"after": str(ObjectId()), "around": str(ObjectId())},
        ],
    )
    async def test_dependencies_before(
        self, app: FastAPI, authorized_client: AsyncClient, server_channel: Channel, query_params
    ):
        print("query", query_params)
        response = await authorized_client.get(f"channels/{str(server_channel.pk)}/messages", params=query_params)
        assert response.status_code == 400
