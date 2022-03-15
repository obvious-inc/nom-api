import logging
from typing import List, Optional

import aiohttp
from aiohttp import FormData
from fastapi import UploadFile

from app.config import get_settings

logger = logging.getLogger(__name__)

CLOUDFLARE_IMAGES_URL = "https://api.cloudflare.com/client/v4/accounts/%s/images/v1"


async def upload_image_url(image_url, prefix: Optional[str] = ""):
    filename = image_url
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            if not response.ok:
                response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            content = await response.read()
            image_data = await upload_content(
                content=content, filename=filename, content_type=content_type, prefix=prefix
            )
            return image_data


async def upload_images(files: List[UploadFile], prefix: Optional[str] = ""):
    images = []
    for file in files:
        content = await file.read()
        image_data = await upload_content(
            content=content, filename=file.filename, content_type=file.content_type, prefix=prefix
        )
        images.append(image_data)
    return images


async def upload_content(
    content, filename: str, content_type: str, metadata: Optional[dict] = None, prefix: Optional[str] = ""
) -> dict:
    settings = get_settings()
    account_id = settings.cloudflare_account_id
    url = CLOUDFLARE_IMAGES_URL % account_id
    headers = {"Authorization": f"Bearer {settings.cloudflare_images_api_token}"}

    async with aiohttp.ClientSession(headers=headers) as session:
        data = FormData()
        if prefix:
            filename = f"{prefix}.{filename}"
        data.add_field("file", value=content, filename=filename, content_type=content_type)
        if metadata:
            data.add_field("metadata", metadata)

        async with session.post(url, data=data) as resp:
            if not resp.ok:
                logger.warning(f"problem storing file {filename}: {resp.status} {resp.text}")
                resp.raise_for_status()
            json_resp = await resp.json()
            result = json_resp["result"]
            image_data = {"id": result["id"], "filename": result["filename"], "variants": result["variants"]}
            return image_data
