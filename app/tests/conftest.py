import binascii
import json
import os
import secrets

import arrow
import pytest
from asgi_lifespan import LifespanManager
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import FastAPI
from httpx import AsyncClient
from web3 import Web3

from app.helpers.database import get_client, get_db
from app.main import get_application
from app.services.auth import generate_wallet_token


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


@pytest.fixture(scope="module")
def private_key() -> bytes:
    key = secrets.token_bytes(32)
    return key


@pytest.fixture(scope="module")
def wallet(private_key: bytes) -> str:
    priv = binascii.hexlify(private_key).decode('ascii')
    private_key = "0x" + priv
    acct = Account.from_key(private_key)
    return acct.address


@pytest.fixture
async def authorized_client(client: AsyncClient, private_key: bytes, wallet: str) -> AsyncClient:
    message_data = {
        "address": wallet,
        "signed_at": arrow.utcnow().isoformat()
    }

    str_message = json.dumps(message_data, separators=(',', ':'))
    message = encode_defunct(text=str_message)
    signed_message = Web3().eth.account.sign_message(message, private_key=private_key)

    data = {
        "message": message_data,
        "signature": signed_message.signature
    }

    access_token = await generate_wallet_token(data)

    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {access_token}",
    }

    yield client
    client.headers.pop("Authorization")
