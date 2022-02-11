from app.helpers.giphy import GiphyClient
from app.helpers.tenor import TenorClient


async def _get_giphy_search(search_term: str, media_filter: str):
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


async def _get_tenor_search(search_term: str, media_filter: str):
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
            }
        )
    return gifs


async def get_gifs_search(search_term: str, media_filter: str, provider: str):
    if provider == "giphy":
        gifs = await _get_giphy_search(search_term=search_term, media_filter=media_filter)
    elif provider == "tenor":
        gifs = await _get_tenor_search(search_term=search_term, media_filter=media_filter)
    else:
        raise Exception(f"unexpected GIF provider: {provider}")

    return gifs
