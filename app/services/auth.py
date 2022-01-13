import json

import arrow

from app.helpers.jwt import generate_jwt_token
from app.helpers.w3 import get_wallet_address_from_signed_message


async def generate_wallet_token(data: dict) -> str:
    message = data.get("message")
    signature = data.get("signature")

    if not message or not signature:
        raise Exception("missing params")

    json_message = json.dumps(message)

    try:
        signed_address = get_wallet_address_from_signed_message(json_message, signature)
    except Exception as e:
        raise e

    assert signed_address == message.get("address")
    signed_at = arrow.get(message.get("signed_at"))
    assert signed_at > arrow.utcnow().shift(seconds=-5)

    token = generate_jwt_token({"sub": signed_address})
    return token
