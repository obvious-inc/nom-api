import pytest
from bson import ObjectId
from fastapi import FastAPI
from httpx import AsyncClient

from app.dependencies import common_parameters
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
    async def test_common_params_before_or_after_or_around_only(
        self, app: FastAPI, authorized_client: AsyncClient, server_channel: Channel, query_params
    ):
        response = await authorized_client.get(f"channels/{str(server_channel.pk)}/messages", params=query_params)
        assert response.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.parametrize("limit", [0, -20, 500, "hey"])
    async def test_common_params_limit_within_limits_and_int(
        self,
        app: FastAPI,
        authorized_client: AsyncClient,
        server_channel: Channel,
        limit: int,
    ):
        response = await authorized_client.get(f"channels/{str(server_channel.pk)}/messages?limit={limit}")
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "sort, sort_by_field, sort_by_direction",
        [
            ("-created_at", "created_at", -1),
            ("created_at", "created_at", 1),
            ("-author", "author", -1),
            ("author", "author", 1),
        ],
    )
    async def test_common_params_sort_as_one_string(
        self,
        app: FastAPI,
        authorized_client: AsyncClient,
        server_channel: Channel,
        sort,
        sort_by_field,
        sort_by_direction,
    ):
        params = await common_parameters(sort=sort)
        assert params["sort_by_field"] == sort_by_field
        assert params["sort_by_direction"] == sort_by_direction
