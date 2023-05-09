import time
from datetime import datetime
from typing import Callable

import arrow
import pytest
from cryptography.hazmat.primitives._serialization import Encoding, PublicFormat
from eth_account.datastructures import SignedMessage
from eth_account.messages import encode_defunct
from fastapi import HTTPException
from web3 import Web3
from web3.auto import w3

from app.config import get_settings
from app.helpers.crypto import create_ed25519_keypair
from app.helpers.jwt import decode_jwt_token
from app.helpers.w3 import (
    get_signable_message_for_broadcast_identity_payload,
    get_wallet_address_from_broadcast_identity_payload,
)
from app.models.auth import RefreshToken
from app.models.server import Server
from app.models.user import User
from app.schemas.auth import AccountBroadcastIdentitySchema, AuthWalletSchema, RefreshTokenCreateSchema
from app.services.auth import broadcast_user_identity, create_refresh_token, generate_wallet_token, revoke_tokens
from app.services.crud import delete_item, get_item, get_items, update_item
from app.services.users import get_user_by_id


class TestAuthService:
    @pytest.mark.asyncio
    async def test_generate_wallet_token_ok(self, db, private_key: bytes, wallet: str, server: Server):
        nonce = 1234
        signed_at = arrow.utcnow().isoformat()
        message = f"""NOM wants you to sign in with your web3 account

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

    @pytest.mark.asyncio
    async def test_generate_access_token_missing_signed_at_in_message(
        self, db, private_key: bytes, wallet: str, server: Server, get_signed_message_data: Callable
    ):
        nonce = 1234
        signed_at = arrow.utcnow().isoformat()
        message = f"""NOM wants you to sign in with your web3 account

                        {wallet}

                        URI: localhost
                        Nonce: {nonce}"""

        encoded_message = encode_defunct(text=message)
        signed_message = Web3().eth.account.sign_message(encoded_message, private_key=private_key)

        data = {
            "message": message,
            "signature": signed_message.signature.hex(),
            "signed_at": signed_at,
            "nonce": nonce,
            "address": wallet,
        }

        with pytest.raises(AssertionError) as exc_info:
            await generate_wallet_token(AuthWalletSchema(**data))

        assert "signed_at not found" in exc_info.value.args

    @pytest.mark.asyncio
    async def test_generate_access_token_missing_nonce_in_message(
        self, db, private_key: bytes, wallet: str, server: Server, get_signed_message_data: Callable
    ):
        nonce = 1234
        signed_at = arrow.utcnow().isoformat()
        message = f"""NOM wants you to sign in with your web3 account

                            {wallet}

                            URI: localhost
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

        with pytest.raises(AssertionError) as exc_info:
            await generate_wallet_token(AuthWalletSchema(**data))

        assert "nonce not found" in exc_info.value.args

    @pytest.mark.asyncio
    async def test_generate_access_token_and_refresh_token(
        self, db, private_key: bytes, wallet: str, server: Server, get_signed_message_data: Callable
    ):
        data = await get_signed_message_data(private_key, wallet)
        token = await generate_wallet_token(AuthWalletSchema(**data))

        assert getattr(token, "access_token") is not None
        assert getattr(token, "refresh_token") is not None

        decrypted_token = decode_jwt_token(token.access_token)
        token_user_id = decrypted_token.get("sub")
        user = await get_user_by_id(user_id=token_user_id)
        assert user.wallet_address == wallet

        refresh_tokens = await get_items(filters={"user": user.pk}, result_obj=RefreshToken)
        assert len(refresh_tokens) == 1

        assert refresh_tokens[0].refresh_token == token.refresh_token

    @pytest.mark.asyncio
    async def test_refresh_token_ok(
        self, db, private_key: bytes, wallet: str, current_user: User, server: Server, get_signed_message_data: Callable
    ):
        data = await get_signed_message_data(private_key, wallet)
        token = await generate_wallet_token(AuthWalletSchema(**data))

        refresh_tokens = await get_items(filters={"user": current_user.pk}, result_obj=RefreshToken)
        assert len(refresh_tokens) == 1
        assert refresh_tokens[0].refresh_token == token.refresh_token

        refresh_token_model = RefreshTokenCreateSchema(user=str(current_user.pk), refresh_token=token.refresh_token)
        new_token = await create_refresh_token(token_model=refresh_token_model)

        assert getattr(new_token, "access_token") is not None
        assert getattr(new_token, "refresh_token") is not None

        refresh_tokens = await get_items(filters={"user": current_user.pk}, result_obj=RefreshToken)
        assert len(refresh_tokens) == 2
        assert refresh_tokens[0].refresh_token == new_token.refresh_token
        assert refresh_tokens[0].used is False

        assert refresh_tokens[1].refresh_token == token.refresh_token
        assert refresh_tokens[1].used is True

    @pytest.mark.asyncio
    async def test_refresh_token_already_used(
        self, db, private_key: bytes, wallet: str, current_user: User, server: Server, get_signed_message_data: Callable
    ):
        data = await get_signed_message_data(private_key, wallet)
        token = await generate_wallet_token(AuthWalletSchema(**data))

        db_refresh_token = await get_item(filters={"user": current_user.pk}, result_obj=RefreshToken)
        await update_item(db_refresh_token, data={"used": True})

        refresh_token_model = RefreshTokenCreateSchema(user=str(current_user.pk), refresh_token=token.refresh_token)
        with pytest.raises(HTTPException) as e_info:
            await create_refresh_token(token_model=refresh_token_model)

        assert "already used" in e_info.value.detail

    @pytest.mark.asyncio
    async def test_refresh_token_non_existing(
        self, db, private_key: bytes, wallet: str, current_user: User, server: Server, get_signed_message_data: Callable
    ):
        data = await get_signed_message_data(private_key, wallet)
        token = await generate_wallet_token(AuthWalletSchema(**data))

        db_refresh_token = await get_item(filters={"user": current_user.pk}, result_obj=RefreshToken)
        await delete_item(db_refresh_token)

        refresh_token_model = RefreshTokenCreateSchema(user=str(current_user.pk), refresh_token=token.refresh_token)
        with pytest.raises(HTTPException) as e_info:
            await create_refresh_token(token_model=refresh_token_model)

        assert "not find refresh token" in e_info.value.detail

    @pytest.mark.asyncio
    async def test_refresh_token_old_not_used(
        self, db, private_key: bytes, wallet: str, current_user: User, server: Server, get_signed_message_data: Callable
    ):
        data = await get_signed_message_data(private_key, wallet)
        settings = get_settings()
        old_expiry = settings.jwt_refresh_token_expire_minutes
        settings.jwt_refresh_token_expire_minutes = -1
        token = await generate_wallet_token(AuthWalletSchema(**data))
        settings.jwt_refresh_token_expire_minutes = old_expiry

        decrypted_token = decode_jwt_token(token.refresh_token, options={"verify_exp": False})
        token_expiry = decrypted_token.get("exp")
        expiry_date = datetime.fromtimestamp(token_expiry)
        assert expiry_date <= datetime.now()

        refresh_token_model = RefreshTokenCreateSchema(user=str(current_user.pk), refresh_token=token.refresh_token)
        with pytest.raises(HTTPException) as e_info:
            await create_refresh_token(token_model=refresh_token_model)

        assert "could not validate token" in e_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_revoke_tokens(
        self, db, private_key: bytes, wallet: str, current_user: User, server: Server, get_signed_message_data: Callable
    ):
        data = await get_signed_message_data(private_key, wallet)
        token = await generate_wallet_token(AuthWalletSchema(**data))

        refresh_tokens = await get_items(filters={"user": current_user.pk}, result_obj=RefreshToken)
        assert len(refresh_tokens) == 1
        assert refresh_tokens[0].refresh_token == token.refresh_token

        await revoke_tokens(current_user=current_user)

        refresh_tokens = await get_items(filters={"user": current_user.pk}, result_obj=RefreshToken)
        assert len(refresh_tokens) == 0

    @pytest.mark.asyncio
    async def test_refresh_token_already_used_revoke_all(
        self, db, private_key: bytes, wallet: str, current_user: User, server: Server, get_signed_message_data: Callable
    ):
        data = await get_signed_message_data(private_key, wallet)
        token = await generate_wallet_token(AuthWalletSchema(**data))

        refresh_tokens = await get_items(filters={"user": current_user.pk}, result_obj=RefreshToken)
        assert len(refresh_tokens) == 1
        assert refresh_tokens[0].refresh_token == token.refresh_token

        refresh_token_model = RefreshTokenCreateSchema(user=str(current_user.pk), refresh_token=token.refresh_token)
        new_token = await create_refresh_token(token_model=refresh_token_model)

        assert getattr(new_token, "access_token") is not None
        assert getattr(new_token, "refresh_token") is not None

        refresh_tokens = await get_items(filters={"user": current_user.pk}, result_obj=RefreshToken)
        assert len(refresh_tokens) == 2
        assert refresh_tokens[0].refresh_token == new_token.refresh_token
        assert refresh_tokens[0].used is False

        assert refresh_tokens[1].refresh_token == token.refresh_token
        assert refresh_tokens[1].used is True

        refresh_token_model = RefreshTokenCreateSchema(user=str(current_user.pk), refresh_token=token.refresh_token)
        with pytest.raises(HTTPException) as e_info:
            await create_refresh_token(token_model=refresh_token_model)

        assert "already used" in e_info.value.detail
        refresh_tokens = await get_items(filters={"user": current_user.pk}, result_obj=RefreshToken)
        assert len(refresh_tokens) == 0

    @pytest.mark.asyncio
    async def test_generate_wallet_signature_expired(self, db, private_key: bytes, wallet: str, server: Server):
        nonce = 1234
        signed_at = arrow.utcnow().shift(minutes=-2).isoformat()
        message = f"""NOM wants you to sign in with your web3 account

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

        with pytest.raises(HTTPException):
            await generate_wallet_token(AuthWalletSchema(**data))

    @pytest.mark.asyncio
    async def test_broadcast_account_identity_ok(self, db, private_key: bytes, wallet: str):
        user = await get_item(filters={"wallet_address": wallet}, result_obj=User)
        assert user is None

        signer_private_key, signer_public_key = await create_ed25519_keypair()
        signer_str_public_key = (
            "0x" + signer_public_key.public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw).hex()
        )

        to_sign_input_struct = {
            "account": wallet,
            "timestamp": int(time.time() * 1000),
            "type": "account-broadcast",
            "body": {"signers": [{"public_key": signer_str_public_key}]},
        }

        signable_message = await get_signable_message_for_broadcast_identity_payload(to_sign_input_struct)
        signed_message: SignedMessage = w3.eth.account.sign_message(signable_message, private_key=private_key.hex())
        signature: str = signed_message.signature.hex()
        assert wallet == await get_wallet_address_from_broadcast_identity_payload(to_sign_input_struct, signature)

        data = {
            "headers": {"signature_scheme": "EIP-712", "hash_scheme": "SHA256", "signature": signature},
            "payload": to_sign_input_struct,
        }

        await broadcast_user_identity(AccountBroadcastIdentitySchema(**data))

        user = await get_item(filters={"wallet_address": wallet}, result_obj=User)
        assert user is not None
        assert len(user.signers) == 1
        assert user.signers[0] == signer_str_public_key

    @pytest.mark.asyncio
    async def test_broadcast_account_identity_wrong_signer(self, db, private_key: bytes, wallet: str):
        user = await get_item(filters={"wallet_address": wallet}, result_obj=User)
        assert user is None

        signer_private_key, signer_public_key = await create_ed25519_keypair()
        signer_str_public_key = (
            "0x" + signer_public_key.public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw).hex()
        )

        another_wallet = Web3().eth.account.create().address

        to_sign_input_struct = {
            "account": another_wallet,
            "timestamp": int(time.time() * 1000),
            "type": "account-broadcast",
            "body": {"signers": [{"public_key": signer_str_public_key}]},
        }

        signable_message = await get_signable_message_for_broadcast_identity_payload(to_sign_input_struct)
        signed_message: SignedMessage = w3.eth.account.sign_message(signable_message, private_key=private_key.hex())
        signature: str = signed_message.signature.hex()
        assert wallet == await get_wallet_address_from_broadcast_identity_payload(to_sign_input_struct, signature)

        data = {
            "headers": {"signature_scheme": "EIP-712", "hash_scheme": "SHA256", "signature": signature},
            "payload": to_sign_input_struct,
        }

        with pytest.raises(HTTPException) as e_info:
            await broadcast_user_identity(AccountBroadcastIdentitySchema(**data))

        assert "signature_invalid" == e_info.value.detail

        user = await get_item(filters={"wallet_address": wallet}, result_obj=User)
        assert user is None

    @pytest.mark.asyncio
    async def test_broadcast_account_identity_expired_timestamp(self, db, private_key: bytes, wallet: str):
        user = await get_item(filters={"wallet_address": wallet}, result_obj=User)
        assert user is None

        signer_private_key, signer_public_key = await create_ed25519_keypair()
        signer_str_public_key = (
            "0x" + signer_public_key.public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw).hex()
        )

        to_sign_input_struct = {
            "account": wallet,
            "timestamp": int(time.time() * 1000) - 3600 * 1000,
            "type": "account-broadcast",
            "body": {"signers": [{"public_key": signer_str_public_key}]},
        }

        signable_message = await get_signable_message_for_broadcast_identity_payload(to_sign_input_struct)
        signed_message: SignedMessage = w3.eth.account.sign_message(signable_message, private_key=private_key.hex())
        signature: str = signed_message.signature.hex()
        assert wallet == await get_wallet_address_from_broadcast_identity_payload(to_sign_input_struct, signature)

        data = {
            "headers": {"signature_scheme": "EIP-712", "hash_scheme": "SHA256", "signature": signature},
            "payload": to_sign_input_struct,
        }

        with pytest.raises(HTTPException) as e_info:
            await broadcast_user_identity(AccountBroadcastIdentitySchema(**data))

        assert "signature_expired" == e_info.value.detail

        user = await get_item(filters={"wallet_address": wallet}, result_obj=User)
        assert user is None

    @pytest.mark.asyncio
    async def test_broadcast_account_identity_unknown_sig_scheme(self, db, private_key: bytes, wallet: str):
        user = await get_item(filters={"wallet_address": wallet}, result_obj=User)
        assert user is None

        signer_private_key, signer_public_key = await create_ed25519_keypair()
        signer_str_public_key = (
            "0x" + signer_public_key.public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw).hex()
        )

        to_sign_input_struct = {
            "account": wallet,
            "timestamp": int(time.time() * 1000) - 3600 * 1000,
            "type": "account-broadcast",
            "body": {"signers": [{"public_key": signer_str_public_key}]},
        }

        signable_message = await get_signable_message_for_broadcast_identity_payload(to_sign_input_struct)
        signed_message: SignedMessage = w3.eth.account.sign_message(signable_message, private_key=private_key.hex())
        signature: str = signed_message.signature.hex()
        assert wallet == await get_wallet_address_from_broadcast_identity_payload(to_sign_input_struct, signature)

        data = {
            "headers": {"signature_scheme": "eip-191", "hash_scheme": "SHA256", "signature": signature},
            "payload": to_sign_input_struct,
        }

        with pytest.raises(NotImplementedError) as e_info:
            await broadcast_user_identity(AccountBroadcastIdentitySchema(**data))

        assert "unexpected signature scheme" in str(e_info.value)

        user = await get_item(filters={"wallet_address": wallet}, result_obj=User)
        assert user is None

    @pytest.mark.asyncio
    async def test_broadcast_account_identity_unknown_hash_scheme(self, db, private_key: bytes, wallet: str):
        user = await get_item(filters={"wallet_address": wallet}, result_obj=User)
        assert user is None

        signer_private_key, signer_public_key = await create_ed25519_keypair()
        signer_str_public_key = (
            "0x" + signer_public_key.public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw).hex()
        )

        to_sign_input_struct = {
            "account": wallet,
            "timestamp": int(time.time() * 1000),
            "type": "account-broadcast",
            "body": {"signers": [{"public_key": signer_str_public_key}]},
        }

        signable_message = await get_signable_message_for_broadcast_identity_payload(to_sign_input_struct)
        signed_message: SignedMessage = w3.eth.account.sign_message(signable_message, private_key=private_key.hex())
        signature: str = signed_message.signature.hex()
        assert wallet == await get_wallet_address_from_broadcast_identity_payload(to_sign_input_struct, signature)

        data = {
            "headers": {"signature_scheme": "eip-712", "hash_scheme": "sha512", "signature": signature},
            "payload": to_sign_input_struct,
        }

        with pytest.raises(NotImplementedError) as e_info:
            await broadcast_user_identity(AccountBroadcastIdentitySchema(**data))

        assert "unexpected hash scheme" in str(e_info.value)

        user = await get_item(filters={"wallet_address": wallet}, result_obj=User)
        assert user is None

    @pytest.mark.asyncio
    async def test_broadcast_account_identity_empty_signers(self, db, private_key: bytes, wallet: str):
        user = await get_item(filters={"wallet_address": wallet}, result_obj=User)
        assert user is None

        to_sign_input_struct = {
            "account": wallet,
            "timestamp": int(time.time() * 1000),
            "type": "account-broadcast",
            "body": {"signers": []},
        }

        signable_message = await get_signable_message_for_broadcast_identity_payload(to_sign_input_struct)
        signed_message: SignedMessage = w3.eth.account.sign_message(signable_message, private_key=private_key.hex())
        signature: str = signed_message.signature.hex()
        assert wallet == await get_wallet_address_from_broadcast_identity_payload(to_sign_input_struct, signature)

        data = {
            "headers": {"signature_scheme": "eip-712", "hash_scheme": "sha256", "signature": signature},
            "payload": to_sign_input_struct,
        }

        with pytest.raises(HTTPException) as e_info:
            await broadcast_user_identity(AccountBroadcastIdentitySchema(**data))

        assert "no signers found" in e_info.value.detail

        user = await get_item(filters={"wallet_address": wallet}, result_obj=User)
        assert user is None
