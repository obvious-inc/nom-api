from typing import Optional

import aiohttp
from aiohttp import ClientTimeout


class SingletonHTTPClient:
    aiohttp_client: Optional[aiohttp.ClientSession] = None

    @classmethod
    def get_aiohttp_client(cls) -> aiohttp.ClientSession:
        if cls.aiohttp_client is None:
            cls.aiohttp_client = aiohttp.ClientSession(timeout=ClientTimeout(total=5))

        return cls.aiohttp_client

    @classmethod
    async def close_aiohttp_client(cls) -> None:
        if cls.aiohttp_client:
            await cls.aiohttp_client.close()
            cls.aiohttp_client = None

    @classmethod
    async def query_url(cls, url: str, headers=None):
        client = cls.get_aiohttp_client()

        async with client.get(url, headers=headers) as response:
            if not response.ok:
                response.raise_for_status()

            text_result = await response.text()

        return text_result


async def unfurl_singleton_start() -> None:
    SingletonHTTPClient.get_aiohttp_client()


async def unfurl_singleton_shutdown() -> None:
    await SingletonHTTPClient.close_aiohttp_client()
