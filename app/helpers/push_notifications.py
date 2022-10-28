import json
import logging
import zlib
from typing import List

import aiohttp

from app.helpers.events import EventType

logger = logging.getLogger(__name__)


async def _broadcast_expo_notifications(push_tokens: List[str], data: dict):
    logger.debug(f"push notification: {json.dumps(data)}")

    if not push_tokens:
        logger.info("no tokens to push notifications to")
        return

    headers = {
        "host": "exp.host",
        "accept": "application/json",
        "accept-encoding": "gzip, deflate",
        "content-type": "application/json",
        "content-encoding": "gzip",
    }

    data["to"] = push_tokens
    compressed_data = zlib.compress(json.dumps(data).encode("utf-8"))

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
                    logger.warning(f"should remove token: {push_tokens[index]}")
                else:
                    logger.error(f"unhandled push error: {ticket}")


async def broadcast_push_event(event: EventType, data: dict, push_tokens: List[str]):
    await _broadcast_expo_notifications(push_tokens, data=data)
