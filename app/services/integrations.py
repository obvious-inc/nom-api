from typing import Optional
from urllib.parse import urlparse

from app.helpers.giphy import GiphyClient
from app.helpers.tenor import TenorClient


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
