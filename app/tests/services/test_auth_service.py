import json

import arrow
import pytest
from bson import ObjectId
from eth_account.messages import encode_defunct
from web3 import Web3

from app.helpers.jwt import decode_jwt_token
from app.models.user import User
from app.services.auth import generate_wallet_token


class TestAuthService:
    @pytest.mark.asyncio
    async def test_generate_wallet_token_ok(self, db, private_key: bytes, wallet: str):
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

        token = await generate_wallet_token(data)
        decrypted_token = decode_jwt_token(token)
        token_user_id = decrypted_token.get("sub")
        assert token_user_id != wallet

        user = await User.find_one({'_id': ObjectId(token_user_id)})
        assert user is not None
        assert user.wallet_address == wallet
