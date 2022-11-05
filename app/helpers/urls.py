import logging
import re
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

META_TAG_PATTERN = re.compile(r"<meta[^>]+>", flags=re.IGNORECASE)
FAVICON_PATTERN = re.compile('<link rel="(?:shortcut )?icon" href="(.+?)"', flags=re.IGNORECASE)
TITLE_PATTERN = re.compile("<title>(.+?)</title>", flags=re.IGNORECASE)

INTERESTING_METATAGS = [
    "title",
    "description",
    "og:type",
    "og:url",
    "og:title",
    "og:description",
    "og:image",
    "twitter:card",
    "twitter:url",
    "twitter:title",
    "twitter:description",
    "twitter:image",
]


async def extract_metatags_from_html(html: str) -> dict:
    metatags = {}

    all_metatags = re.findall(META_TAG_PATTERN, html)
    for metatag in all_metatags:
        matches = re.findall(r'property="(.+?)".+?content="(.+?)"', metatag)
        if not matches:
            continue

        key = matches[0][0]
        if key not in INTERESTING_METATAGS:
            continue

        content = matches[0][1]
        metatags[key] = content

    return metatags


async def extract_favicon_from_html(html: str) -> str:
    favicon_match = re.search(FAVICON_PATTERN, html)
    if not favicon_match:
        return ""

    return favicon_match.group(1)


async def unfurl_url(url: str) -> Optional[dict]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.text()

            if not resp.ok:
                logger.error(f"{resp.status} {text} | problem fetching url: {url}")
                return None

            metatags = await extract_metatags_from_html(text)
            favicon = await extract_favicon_from_html(text)
            title_match = re.search(TITLE_PATTERN, text)

            return {"url": url, "favicon": favicon, "title": title_match.group(1) if title_match else "", **metatags}
