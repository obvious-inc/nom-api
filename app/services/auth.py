import asyncio

import arrow

from app.helpers.jwt import generate_jwt_token
from app.helpers.w3 import checksum_address, get_wallet_address_from_signed_message
from app.models.server import Server
from app.schemas.users import UserCreateSchema
from app.services.crud import get_items
from app.services.servers import join_server
from app.services.users import create_user, get_user_by_id, get_user_by_wallet_address

SIGNATURE_VALID_SECONDS = 30


async def add_user_to_default_server(user_id):
    user = await get_user_by_id(user_id=user_id)
    servers = await get_items(filters={}, result_obj=Server, current_user=user, size=1, sort_by_direction=1)
    server = servers[0]
    await join_server(server=server, current_user=user)


async def generate_wallet_token(data: dict) -> str:
    message = data.get("message")
    signature = data.get("signature")

    if not message or not signature:
        raise Exception("missing params")

    address = data.get("address")
    signed_at = arrow.get(data.get("signed_at"))
    nonce = data.get("nonce")

    try:
        signed_address = get_wallet_address_from_signed_message(message, signature)
    except Exception as e:
        raise e

    assert signed_address == checksum_address(address)
    assert signed_address.lower() in message.lower()
    assert signed_at > arrow.utcnow().shift(seconds=-SIGNATURE_VALID_SECONDS)
    assert f"nonce: {nonce}" in message.lower()

    user = await get_user_by_wallet_address(wallet_address=signed_address)
    if not user:
        user = await create_user(UserCreateSchema(wallet_address=signed_address), fetch_ens=True)

        # TODO: delete this once things are live
        asyncio.create_task(add_user_to_default_server(user_id=str(user.id)))

    token = generate_jwt_token({"sub": str(user.id)})
    return token
