import json
import time

import arrow
import pytest
from bson import ObjectId
from eth_account.datastructures import SignedMessage
from eth_account.messages import encode_defunct
from fastapi import FastAPI
from httpx import AsyncClient
from pymongo.database import Database
from web3 import Web3

from app.helpers.jwt import decode_jwt_token
from app.models.user import User


class TestAuthRoutes:
    @pytest.mark.asyncio
    async def test_create_token_wallet_ok(self, app: FastAPI,
                                          db: Database,
                                          client: AsyncClient,
                                          private_key: bytes,
                                          wallet: str):
        message_data = {
            "address": wallet,
            "signed_at": arrow.utcnow().isoformat()
        }
        str_message = json.dumps(message_data)
        message = encode_defunct(text=str_message)
        signed_message = Web3().eth.account.sign_message(message, private_key=private_key)  # type: SignedMessage

        data = {
            "message": message_data,
            "signature": signed_message.signature.hex()
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
        user = await User.find_one({'_id': ObjectId(token_user_id)})
        assert user is not None
        assert user.wallet_address == wallet

    @pytest.mark.asyncio
    async def test_login_with_same_wallet(self, app: FastAPI,
                                          db: Database,
                                          client: AsyncClient,
                                          private_key: bytes,
                                          wallet: str):
        message_data = {
            "address": wallet,
            "signed_at": arrow.utcnow().isoformat()
        }
        str_message = json.dumps(message_data)
        message = encode_defunct(text=str_message)
        signed_message = Web3().eth.account.sign_message(message, private_key=private_key)  # type: SignedMessage

        data = {
            "message": message_data,
            "signature": signed_message.signature.hex()
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
        user = await User.find_one({'_id': ObjectId(token_user_id)})
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
