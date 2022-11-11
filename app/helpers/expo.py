import json
import logging
import zlib
from typing import List

import aiohttp

from app.config import get_settings

logger = logging.getLogger(__name__)


async def send_expo_push_notifications(push_messages: List[str]):
    logger.debug(f"push notifications: {json.dumps(push_messages)}")

    if not push_messages:
        logger.info("no tokens to push notifications to")
        return

    settings = get_settings()

    headers = {
        "host": "exp.host",
        "accept": "application/json",
        "accept-encoding": "gzip, deflate",
        "content-type": "application/json",
        "content-encoding": "gzip",
        "authorization": f"bearer {settings.expo_access_token}",
    }

    compressed_data = zlib.compress(json.dumps(push_messages).encode("utf-8"))

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post("https://exp.host/--/api/v2/push/send", data=compressed_data) as resp:
            if not resp.ok:
                text = await resp.text()
                logger.error(f"problem pushing notifications: {resp.status} {text}")
                raise Exception("problem with notifications")

            json_resp = await resp.json()
            tickets = json_resp.get("data")

            for index, ticket in enumerate(tickets):
                status = ticket.get("status")
                if status == "ok":
                    continue

                details = ticket.get("details")
                error = details.get("error")
                if error == "DeviceNotRegistered":
                    error_token = details.get("expoPushToken")
                    logger.warning(f"should remove token: {error_token}")
                else:
                    logger.error(f"unhandled push error: {ticket}")
