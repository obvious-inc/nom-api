import logging

import aiohttp

from app.config import get_settings

logger = logging.getLogger(__name__)

SIMPLEHASH_BASE_URL = "https://api.simplehash.com/api/v0"


async def get_image_url(token: dict) -> str:
    image_url = token.get("external_url")
    metadata = token.get("extra_metadata", {})
    image_url = metadata.get("image_original_url") or image_url
    image_url = token.get("image_url") or image_url

    if not image_url:
        logger.warning(f"couldn't find image url for nft: {token}")
        return ""

    return image_url


async def get_nft(contract_address: str, token_id: str, chain: str = "ethereum") -> dict:
    settings = get_settings()
    url = f"{SIMPLEHASH_BASE_URL}/nfts/{chain}/{contract_address}/{token_id}"
    headers = {
        "X-Api-Key": settings.alchemy_api_key,
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            return await response.json()
