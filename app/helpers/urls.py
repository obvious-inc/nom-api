import logging
import random
import re
from typing import Optional
from urllib.parse import quote_plus, urlparse, urlunparse

import aiohttp
from bs4 import BeautifulSoup, SoupStrainer

from app.config import get_settings

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36",
    "Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36",
]


meta_tags_strainer = SoupStrainer("meta")
title_tag_strainer = SoupStrainer("title")
favicon_tag_strainer = SoupStrainer("link", rel="icon")
favicon_shortcut_tag_strainer = SoupStrainer("link", rel="shortcut icon")
favicon_alt_tag_strainer = SoupStrainer(href=re.compile("favicon"))
redirect_strainer = SoupStrainer("meta", attrs={"http-equiv": "refresh"})

INTERESTING_METATAGS = [
    "title",
    "description",
    "og:type",
    "og:url",
    "og:title",
    "og:description",
    "og:image",
    "og:video",
    "og:site_name",
    "twitter:card",
    "twitter:url",
    "twitter:title",
    "twitter:description",
    "twitter:image",
]


async def extract_unfurl_info_from_html(html: str, url: str) -> dict:
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
        parsed_url = urlparse(url)
        parsed_url = parsed_url._replace(path=favicon)
        favicon = urlunparse(parsed_url)

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

    if len(metatags) < 2 and url:
        logger.debug("too little metatags extracted, trying with opengraph...")
        metatags = await opengraph_extract_metatags(url)
        if not favicon and "og:favicon" in metatags:
            favicon = metatags["favicon"]

    info = {"title": title, "favicon": favicon, "metatags": metatags}
    return info


async def opengraph_extract_metatags(url: str) -> dict:
    settings = get_settings()
    params = {"app_id": settings.opengraph_app_id}
    async with aiohttp.ClientSession() as session:
        encoded_url = quote_plus(url)
        async with session.get(f"https://opengraph.io/api/1.1/site/{encoded_url}", params=params) as resp:
            if not resp.ok:
                resp.raise_for_status()

            json_resp = await resp.json()
            graph = json_resp.get("hybridGraph")

            metatags = {f"og:{tag}": value for tag, value in graph.items()}
            return metatags


async def unfurl_url(url: str) -> Optional[dict]:
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            text = await resp.text()

            redirect_soup = BeautifulSoup(text, "lxml", parse_only=redirect_strainer)
            redirect_meta = redirect_soup.find("meta")
            if redirect_meta:
                content = redirect_meta.get("content")
                new_url_match = re.match(r"(\d+;url=)?(.+)", content, flags=re.IGNORECASE)
                new_url = new_url_match.group(2) if new_url_match else None
                if new_url:
                    return await unfurl_url(new_url)

            if not resp.ok:
                resp.raise_for_status()

            info = await extract_unfurl_info_from_html(text, url=url)
            return {"url": url, **info}
