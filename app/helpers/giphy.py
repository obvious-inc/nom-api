from typing import Optional

import requests

from app.config import get_settings


class GiphyClient:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.giphy_api_key
        self.search_endpoint = "https://api.giphy.com/v1/gifs/search"
        self.content_filter = "pg-13"
        self.media_filter = "original"

    async def search_gifs(self, search_term: str, limit: int = 10, media_filter: Optional[str] = None):
        params = {
            "q": search_term,
            "limit": limit,
            "api_key": self.api_key,
            "rating": self.content_filter,
            "bundle": media_filter if media_filter else self.media_filter,
        }
        response = requests.get(self.search_endpoint, params=params)
        if not response.ok:
            raise Exception(f"problem fetching gifs. q:{search_term} {response.status_code} {response.text}")

        gifs = response.json().get("data")
        return gifs
