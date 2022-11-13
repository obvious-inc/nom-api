import logging
import re
from typing import Optional

import aiohttp
from bs4 import BeautifulSoup, SoupStrainer

logger = logging.getLogger(__name__)


meta_tags_strainer = SoupStrainer("meta")
title_tag_strainer = SoupStrainer("title")
favicon_tag_strainer = SoupStrainer("link", rel="icon")
favicon_shortcut_tag_strainer = SoupStrainer("link", rel="shortcut icon")
favicon_alt_tag_strainer = SoupStrainer(href=re.compile("favicon"))

INTERESTING_METATAGS = [
    "title",
    "description",
    "og:type",
    "og:url",
    "og:title",
    "og:description",
    "og:image",
    "og:site_name",
    "twitter:card",
    "twitter:url",
    "twitter:title",
    "twitter:description",
    "twitter:image",
]


async def extract_unfurl_info_from_html(html: str, url: str = None) -> dict:
    soup = BeautifulSoup(html, "lxml", parse_only=title_tag_strainer)
    title = soup.title.string if soup.title else ""

    favicon = ""
    metatags = {}

    for strainer in [favicon_tag_strainer, favicon_shortcut_tag_strainer, favicon_alt_tag_strainer]:
        soup = BeautifulSoup(html, "lxml", parse_only=strainer)
        link = soup.find("link")
        if link:
            favicon = link["href"]

            break

    if favicon.startswith("//"):
        favicon = "https:" + favicon

    if favicon.startswith("/") and url is not None:
        if url.endswith("/"):
            favicon = url + favicon[1:]
        else:
            favicon = url + favicon

    meta_soup = BeautifulSoup(html, "lxml", parse_only=meta_tags_strainer)
    for meta_tag in meta_soup.findAll("meta"):
        if meta_tag.get("property") in INTERESTING_METATAGS:
            metatags[meta_tag.get("property")] = meta_tag.get("content")
        elif meta_tag.get("name") in INTERESTING_METATAGS:
            metatags[meta_tag.name] = meta_tag.get("content")
        else:
            continue

    if not title:
        for tag in ["title", "og:title", "og:site_name"]:
            if tag in metatags.keys():
                title = metatags[tag]
                break

    info = {"title": title, "favicon": favicon, "metatags": metatags}
    return info


async def unfurl_url(url: str) -> Optional[dict]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.text()

            if not resp.ok:
                logger.error(f"{resp.status} {text} | problem fetching url: {url}")
                return None

            info = await extract_unfurl_info_from_html(text, url=url)
            return {"url": url, **info}
