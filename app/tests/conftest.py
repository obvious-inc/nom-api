import binascii
import json
import secrets
from typing import Union

import arrow
import pytest
from asgi_lifespan import LifespanManager
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import FastAPI
from httpx import AsyncClient
from web3 import Web3

from app.helpers.database import get_client, get_db, override_get_db
from app.main import get_application
from app.models.base import APIDocument
from app.models.channel import Channel
from app.models.server import Server
from app.models.user import User
from app.schemas.channels import ServerChannelCreateSchema
from app.schemas.servers import ServerCreateSchema
from app.schemas.users import UserCreateSchema
from app.services.auth import generate_wallet_token
from app.services.channels import create_server_channel
from app.services.crud import create_item
from app.services.users import create_user


@pytest.fixture
def app() -> FastAPI:
    app = get_application()
    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with LifespanManager(app):
        async with AsyncClient(app=app, base_url="http://testserver", follow_redirects=True) as client:
            yield client


@pytest.fixture
async def db():
    # TODO: is this the best way for cleaning DB on every test?
    client = await get_client()
    db = await override_get_db()
    await client.drop_database(db.name)
    yield db
    await client.drop_database(db.name)


@pytest.fixture(scope="module")
def private_key() -> bytes:
    key = secrets.token_bytes(32)
    return key


@pytest.fixture(scope="module")
def wallet(private_key: bytes) -> str:
    priv = binascii.hexlify(private_key).decode("ascii")
    private_key = "0x" + priv
    acct = Account.from_key(private_key)
    return acct.address


@pytest.fixture
async def current_user(private_key: bytes, wallet: str) -> User:
    return await create_user(UserCreateSchema(wallet_address=wallet))


@pytest.fixture
async def server(current_user: User) -> Union[Server, APIDocument]:
    server_model = ServerCreateSchema(name="NewShades DAO")
    return await create_item(server_model, result_obj=Server, current_user=current_user, user_field="owner")


@pytest.fixture
async def server_channel(current_user: User, server: Server) -> Union[Channel, APIDocument]:
    server_channel = ServerChannelCreateSchema(kind="server", server=str(server.id), name="testing-channel")
    return await create_server_channel(server_channel, current_user=current_user)


@pytest.fixture
async def authorized_client(client: AsyncClient, private_key: bytes, current_user: User) -> AsyncClient:
    message_data = {"address": current_user.wallet_address, "signed_at": arrow.utcnow().isoformat()}

    str_message = json.dumps(message_data, separators=(",", ":"))
    message = encode_defunct(text=str_message)
    signed_message = Web3().eth.account.sign_message(message, private_key=private_key)

    data = {"message": message_data, "signature": signed_message.signature}

    access_token = await generate_wallet_token(data)

    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {access_token}",
    }

    yield client
    client.headers.pop("Authorization")
