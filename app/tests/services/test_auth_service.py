import arrow
import pytest
from eth_account.messages import encode_defunct
from web3 import Web3

from app.helpers.jwt import decode_jwt_token
from app.models.server import Server
from app.schemas.auth import AuthWalletSchema
from app.services.auth import generate_wallet_token
from app.services.users import get_user_by_id


class TestAuthService:
    @pytest.mark.asyncio
    async def test_generate_wallet_token_ok(self, db, private_key: bytes, wallet: str, server: Server):
        nonce = 1234
        signed_at = arrow.utcnow().isoformat()
        message = f"""NewShades wants you to sign in with your web3 account

            {wallet}

            URI: localhost
            Nonce: {nonce}
            Issued At: {signed_at}"""

        encoded_message = encode_defunct(text=message)
        signed_message = Web3().eth.account.sign_message(encoded_message, private_key=private_key)

        data = {
            "message": message,
            "signature": signed_message.signature.hex(),
            "signed_at": signed_at,
            "nonce": nonce,
            "address": wallet,
        }

        token = await generate_wallet_token(AuthWalletSchema(**data))
        decrypted_token = decode_jwt_token(token.access_token)
        token_user_id = decrypted_token.get("sub")
        assert token_user_id != wallet

        user = await get_user_by_id(user_id=token_user_id)
        assert user is not None
        assert user.wallet_address == wallet
