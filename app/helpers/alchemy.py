import logging

import aiohttp

from app.config import get_settings

logger = logging.getLogger(__name__)

ALCHEMY_BASE_URL = "https://eth-mainnet.alchemyapi.io/v2"


async def get_image_url(token: dict) -> str:
    metadata = token.get("metadata", {})
    image_url = None

    if "external_url" in metadata:
        image_url = metadata.get("external_url")

    if "image" in metadata:
        image_url = metadata.get("image")

    if "image_url" in metadata:
        image_url = metadata.get("image_url")

    if not image_url:
        logger.warning(f"couldn't find image url for nft: {token}")
        return ""

    return image_url


async def get_nft_metadata(contract_address, token_id):
    settings = get_settings()
    url = f"{ALCHEMY_BASE_URL}/{settings.alchemy_api_key}/getNFTMetadata"
    params = {
        "contractAddress": contract_address,
        "tokenId": token_id,
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            return await response.json()


async def get_nft(contract_address: str, token_id: str) -> dict:
    return await get_nft_metadata(contract_address, token_id)
