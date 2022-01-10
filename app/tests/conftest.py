import os

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient

from app.helpers.database import get_db, get_client
from app.main import get_application


@pytest.fixture
def app() -> FastAPI:
    # TODO: be smarter with this
    os.environ["MONGODB_DB"] = "newshades-test"
    
    app = get_application()
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with LifespanManager(app):
        async with AsyncClient(
                app=app,
                base_url="http://testserver",
                follow_redirects=True
        ) as client:
            yield client


@pytest.fixture
async def db(monkeypatch):
    # TODO: is this the best way for cleaning DB on every test?
    client = await get_client()
    db = await get_db()
    await client.drop_database(db.name)
    yield db
    await client.drop_database(db.name)
