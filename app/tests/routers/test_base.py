import arrow
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database


class TestBaseRouting:

    @pytest.mark.asyncio
    async def test_post_fields(self, app: FastAPI, db: Database, authorized_client: AsyncClient):
        server_name = "test"
        response = await authorized_client.post("/servers", json={"name": server_name})
        assert response.status_code == 201
        json_response = response.json()
        assert json_response != {}
        assert 'name' in json_response
        assert '_id' in json_response
        assert isinstance(json_response.get('_id'), str)

        # collection is private
        assert 'collection_name' not in json_response
        assert '_collection_name' not in json_response

        # created_at is isoformat and utc
        assert 'created_at' in json_response
        assert isinstance(json_response.get('created_at'), str)
        created_date = arrow.get(json_response.get('created_at'))
        assert created_date is not None
        assert (arrow.utcnow() - created_date).seconds <= 2
