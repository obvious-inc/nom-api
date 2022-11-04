import http
import logging
from typing import List, Optional
from urllib.parse import urlparse

import aiohttp
from fastapi import HTTPException

from app.config import get_settings
from app.helpers.giphy import GiphyClient
from app.helpers.tenor import TenorClient

logger = logging.getLogger(__name__)


async def _get_giphy_search(search_term: str, media_filter: Optional[str]):
    gifs = []
    giphy_gifs = await GiphyClient().search_gifs(search_term=search_term, media_filter=media_filter)
    for gif in giphy_gifs:
        image = gif.get("images").get("original")
        gifs.append(
            {
                "type": gif.get("type"),
                "url": gif.get("url"),
                "id": gif.get("id"),
                "title": gif.get("title"),
                "src": image.get("url"),
            }
        )
    return gifs


async def _get_tenor_search(search_term: str, media_filter: Optional[str]):
    gifs = []
    tenor_gifs = await TenorClient().search_gifs(search_term=search_term, media_filter=media_filter)
    for gif in tenor_gifs:
        image = gif.get("media")[0].get("gif")
        gifs.append(
            {
                "type": gif.get("type", "gif"),
                "url": gif.get("itemurl"),
                "id": gif.get("id"),
                "title": gif.get("content_description"),
                "src": image.get("url"),
                "tags": image.get("tags"),
            }
        )
    return gifs


async def get_gifs_search(search_term: str, media_filter: Optional[str], provider: str):
    if provider == "giphy":
        gifs = await _get_giphy_search(search_term=search_term, media_filter=media_filter)
    elif provider == "tenor":
        gifs = await _get_tenor_search(search_term=search_term, media_filter=media_filter)
    else:
        raise Exception(f"unexpected GIF provider: {provider}")

    return gifs


async def get_gif_by_url(gif_url: str):
    parsed_url = urlparse(gif_url)
    gif_id = gif_url.split("-")[-1]
    if parsed_url.hostname and "giphy" in parsed_url.hostname:
        giphy_gif = await GiphyClient().get_gif_by_id(gif_id=gif_id)
        image = giphy_gif.get("images").get("original")
        gif = {
            "provider": "giphy",
            "type": giphy_gif.get("type"),
            "url": giphy_gif.get("url"),
            "id": giphy_gif.get("id"),
            "title": giphy_gif.get("title"),
            "src": image.get("url"),
        }
    elif parsed_url.hostname and "tenor" in parsed_url.hostname:
        tenor_gif = await TenorClient().get_gif_by_id(gif_id=gif_id)
        image = tenor_gif.get("media")[0].get("gif")
        gif = {
            "provider": "tenor",
            "type": tenor_gif.get("type", "gif"),
            "url": tenor_gif.get("itemurl"),
            "id": tenor_gif.get("id"),
            "title": tenor_gif.get("content_description"),
            "src": image.get("url"),
        }
    else:
        raise Exception(f"unexpected GIF domain: {parsed_url.hostname}")

    return gif


async def generate_dalle_image(prompt: str):
    settings = get_settings()
    url = "https://api.openai.com/v1/images/generations"

    headers = {
        "Authorization": f"Bearer {settings.dalle_api_key}",
        "Content-Type": "application/json",
    }

    json_data = {"prompt": prompt, "n": 1, "size": "512x512"}

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json=json_data) as response:
            json_response = await response.json()
            data: List[dict] = json_response.get("data")

            if not data or len(data) == 0:
                logger.debug(f"DALL-E response: {json_response}")
                raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST)

            return data[0]
