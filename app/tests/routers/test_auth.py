import asyncio
import binascii
import random
import secrets
import time

import arrow
import pytest
from eth_account import Account
from eth_account.datastructures import SignedMessage
from eth_account.messages import encode_defunct
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database
from web3 import Web3

from app.helpers.jwt import decode_jwt_token
from app.models.server import Server, ServerMember
from app.models.user import User
from app.services.crud import get_items
from app.services.users import get_user_by_id


class TestAuthRoutes:
    @pytest.mark.asyncio
    async def test_create_token_wallet_ok(
        self, app: FastAPI, db: Database, client: AsyncClient, private_key: bytes, wallet: str
    ):
        nonce = 1234
        signed_at = arrow.utcnow().isoformat()
        message = f"""NewShades wants you to sign in with your web3 account

        {wallet}

        URI: localhost
        Nonce: {nonce}
        Issued At: {signed_at}`;
        """
        encoded_message = encode_defunct(text=message)
        signed_message = Web3().eth.account.sign_message(
            encoded_message, private_key=private_key
        )  # type: SignedMessage
        data = {
            "message": message,
            "signature": signed_message.signature.hex(),
            "signed_at": signed_at,
            "nonce": nonce,
            "address": wallet,
        }

        response = await client.post("/auth/login", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert "access_token" in json_response
        assert "token_type" in json_response
        assert json_response.get("token_type") == "bearer"
        token = json_response.get("access_token")
        decrypted_token = decode_jwt_token(token)
        token_user_id = decrypted_token.get("sub")
        assert token_user_id != wallet
        user = await get_user_by_id(user_id=token_user_id)
        assert user is not None
        assert user.wallet_address == wallet

    @pytest.mark.asyncio
    async def test_login_with_same_wallet(
        self, app: FastAPI, db: Database, client: AsyncClient, private_key: bytes, wallet: str
    ):
        nonce = 1234
        signed_at = arrow.utcnow().isoformat()
        message = f"""NewShades wants you to sign in with your web3 account

        {wallet}

        URI: localhost
        Nonce: {nonce}
        Issued At: {signed_at}`;
        """
        encoded_message = encode_defunct(text=message)
        signed_message = Web3().eth.account.sign_message(
            encoded_message, private_key=private_key
        )  # type: SignedMessage
        data = {
            "message": message,
            "signature": signed_message.signature.hex(),
            "signed_at": signed_at,
            "nonce": nonce,
            "address": wallet,
        }

        response = await client.post("/auth/login", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert "access_token" in json_response
        assert "token_type" in json_response
        assert json_response.get("token_type") == "bearer"
        token = json_response.get("access_token")
        decrypted_token = decode_jwt_token(token)
        token_user_id = decrypted_token.get("sub")
        assert token_user_id != wallet
        user = await get_user_by_id(user_id=token_user_id)
        assert user is not None
        assert user.wallet_address == wallet

        time.sleep(1)
        response = await client.post("/auth/login", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert "access_token" in json_response
        assert "token_type" in json_response
        assert json_response.get("token_type") == "bearer"
        new_token = json_response.get("access_token")
        assert new_token != token
        decrypted_token = decode_jwt_token(new_token)
        new_token_user_id = decrypted_token.get("sub")
        assert token_user_id == new_token_user_id
        assert new_token_user_id == str(user.id)
        assert user.wallet_address == wallet

    @pytest.mark.asyncio
    async def test_login_wallet_with_lowercase_address(
        self, app: FastAPI, db: Database, client: AsyncClient, private_key: bytes, wallet: str
    ):
        nonce = 1234
        signed_at = arrow.utcnow().isoformat()
        message = f"""NewShades wants you to sign in with your web3 account

        {wallet}

        URI: localhost
        Nonce: {nonce}
        Issued At: {signed_at}`;
        """
        encoded_message = encode_defunct(text=message)
        signed_message = Web3().eth.account.sign_message(
            encoded_message, private_key=private_key
        )  # type: SignedMessage
        data = {
            "message": message,
            "signature": signed_message.signature.hex(),
            "signed_at": signed_at,
            "nonce": nonce,
            "address": wallet.lower(),
        }

        response = await client.post("/auth/login", json=data)
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_token_wallet_default_server(
        self,
        app: FastAPI,
        db: Database,
        client: AsyncClient,
        current_user: User,
        server: Server,
        event_loop,
    ):
        key = secrets.token_bytes(32)
        priv = binascii.hexlify(key).decode("ascii")
        private_key = "0x" + priv
        acct = Account.from_key(private_key)
        wallet = acct.address

        nonce = 1234
        signed_at = arrow.utcnow().isoformat()
        message = f"""NewShades wants you to sign in with your web3 account
        
{wallet}

URI: localhost
Nonce: {nonce}
Issued At: {signed_at}`;
"""
        encoded_message = encode_defunct(text=message)
        signed_message = Web3().eth.account.sign_message(
            encoded_message, private_key=private_key
        )  # type: SignedMessage
        data = {
            "message": message,
            "signature": signed_message.signature.hex(),
            "signed_at": signed_at,
            "nonce": nonce,
            "address": wallet,
        }

        members = await get_items({"server": server.id}, result_obj=ServerMember, current_user=current_user, size=None)
        assert len(members) == 1

        response = await client.post("/auth/login", json=data)
        assert response.status_code == 201
        json_response = response.json()
        assert "access_token" in json_response
        assert "token_type" in json_response
        assert json_response.get("token_type") == "bearer"
        token = json_response.get("access_token")
        decrypted_token = decode_jwt_token(token)
        token_user_id = decrypted_token.get("sub")
        assert token_user_id != wallet
        user = await get_user_by_id(user_id=token_user_id)
        assert user is not None
        assert user.wallet_address == wallet

        await asyncio.sleep(random.random(), loop=event_loop)
        members = await get_items({"server": server.id}, result_obj=ServerMember, current_user=current_user, size=None)
        assert len(members) == 2
