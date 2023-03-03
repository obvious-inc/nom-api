import logging
import time

from starlette.requests import Request

from app.helpers.crypto import verify_keccak_ed25519_signature
from app.services.users import get_user_by_signer

logger = logging.getLogger(__name__)

MAX_REQUEST_TIMESTAMP_DIFF_IN_SECONDS = 5


async def _build_base_encryption_string(request: Request):
    timestamp = request.headers.get("X-Newshades-Timestamp")
    if int(time.time()) - int(timestamp) > MAX_REQUEST_TIMESTAMP_DIFF_IN_SECONDS:
        raise Exception("Timestamp is too old")

    request_body = (await request.body()).decode()

    # request_path var is the request url path + query params if exists
    request_path = request.url.path
    if request.query_params:
        request_path += "?" + str(request.query_params)

    return f"{timestamp}:{request_path}:{request_body}"


async def get_user_from_signed_request(request: Request):
    timestamp = request.headers.get("X-Newshades-Timestamp")
    signature = request.headers.get("X-Newshades-Signature")
    signer = request.headers.get("X-Newshades-Signer")

    if not timestamp or not signature or not signer:
        logger.warning(
            "Missing required headers for signature authentication. [timestamp=%s, signature=%s, signer=%s]",
            timestamp,
            signature,
            signer,
        )
        raise Exception("Missing required headers for signature authentication")

    base_string = await _build_base_encryption_string(request)
    data = base_string.encode()
    signature_bytes = bytes.fromhex(signature)
    signer_bytes = bytes.fromhex(signer[2:])

    await verify_keccak_ed25519_signature(data=data, signature=signature_bytes, signer=signer_bytes)

    user = await get_user_by_signer(signer=signer)
    if not user:
        raise Exception(f"User not found with signer: {signer}")

    return user
