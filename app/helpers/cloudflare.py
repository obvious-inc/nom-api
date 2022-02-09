import logging
from typing import List, Optional

import aiohttp
from aiohttp import FormData
from fastapi import UploadFile

from app.config import get_settings

logger = logging.getLogger(__name__)

CLOUDFLARE_IMAGES_URL = "https://api.cloudflare.com/client/v4/accounts/%s/images/v1"


async def upload_images(files: List[UploadFile], prefix: Optional[str] = ""):
    settings = get_settings()
    account_id = settings.cloudflare_account_id
    url = CLOUDFLARE_IMAGES_URL % account_id

    headers = {"Authorization": f"Bearer {settings.cloudflare_images_api_token}"}

    images = []
    async with aiohttp.ClientSession(headers=headers) as session:
        for file in files:
            content = await file.read()
            data = FormData()
            filename = file.filename
            if prefix:
                filename = f"{prefix}.{filename}"
            data.add_field("file", value=content, filename=filename, content_type=file.content_type)
            async with session.post(url, data=data) as resp:
                if not resp.ok:
                    logger.warning(f"problem storing file {file.filename}: {resp.status} {resp.text}")
                json_resp = await resp.json()
                result = json_resp["result"]
                image_data = {"id": result["id"], "filename": result["filename"], "variants": result["variants"]}
                images.append(image_data)
    return images
