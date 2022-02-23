import re

import arrow

from app.helpers.jwt import generate_jwt_token
from app.helpers.queue_utils import queue_bg_task
from app.helpers.w3 import checksum_address, get_wallet_address_from_signed_message
from app.models.server import Server
from app.schemas.auth import AuthWalletSchema
from app.schemas.users import UserCreateSchema
from app.services.crud import get_items
from app.services.servers import join_server
from app.services.users import create_user, get_user_by_id, get_user_by_wallet_address

SIGNATURE_VALID_SECONDS = 30
NONCE_SIGNATURE_REGEX = re.compile(r"nonce:\s?(.+?)\b", flags=re.IGNORECASE)
SIGNED_AT_SIGNATURE_REGEX = re.compile(r"issued at:\s?(.+?)$", flags=re.IGNORECASE)


async def add_user_to_default_server(user_id):
    user = await get_user_by_id(user_id=user_id)
    servers = await get_items(filters={}, result_obj=Server, current_user=user, size=1, sort_by_direction=1)
    server = servers[0]
    await join_server(server=server, current_user=user)


async def generate_wallet_token(data: AuthWalletSchema) -> str:
    message = data.message
    signature = data.signature

    if not message or not signature:
        raise Exception("missing params")

    address = data.address
    signed_at = arrow.get(data.signed_at)
    nonce = data.nonce

    try:
        signed_address = get_wallet_address_from_signed_message(message, signature)
    except Exception as e:
        raise e

    assert signed_address == checksum_address(address)
    assert signed_address.lower() in message.lower()

    signed_at_groups = re.search(SIGNED_AT_SIGNATURE_REGEX, message)
    if not signed_at_groups:
        raise AssertionError("signed_at not found")
    message_signed_at_str = signed_at_groups.group(1)
    message_signed_at = arrow.get(message_signed_at_str)
    assert signed_at == message_signed_at
    assert signed_at > arrow.utcnow().shift(seconds=-SIGNATURE_VALID_SECONDS)

    # check nonce
    nonce_groups = re.search(NONCE_SIGNATURE_REGEX, message)
    if not nonce_groups:
        raise AssertionError("nonce not found")
    message_nonce = nonce_groups.group(1)
    assert int(message_nonce) == nonce

    user = await get_user_by_wallet_address(wallet_address=signed_address)
    if not user:
        user = await create_user(UserCreateSchema(wallet_address=signed_address), fetch_ens=True)

        # TODO: delete this once things are live
        await queue_bg_task(add_user_to_default_server, str(user.id))

    token = generate_jwt_token({"sub": str(user.id)})
    return token
