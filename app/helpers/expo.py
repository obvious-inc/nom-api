import asyncio
import json
import logging
import random
import zlib
from typing import List

import aiohttp

from app.config import get_settings
from app.models.user import User
from app.services.crud import find_and_update_item

logger = logging.getLogger(__name__)


async def expo_push(headers, data, attempts=0, max_retries=5):
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.post("https://exp.host/--/api/v2/push/send", data=data) as resp:
                if not resp.ok:
                    if resp.status == 429 or str(resp.status).startswith("5"):
                        if attempts >= max_retries:
                            logger.error(f"unable to send notifications. max retries exceeded ({max_retries})")
                            resp.raise_for_status()

                        attempts += 1
                        delay = 2**attempts + random.uniform(0, 1)
                        logger.warning(
                            f"notifications failed (attempt {attempts}), waiting {delay:.2f}s and trying again. {resp.status}"
                        )
                        await asyncio.sleep(delay)
                        return await expo_push(headers, data, attempts=attempts)

                return await resp.json()
        except Exception as e:
            attempts += 1
            delay = 2**attempts + random.uniform(0, 1)
            await asyncio.sleep(delay)
            logger.warning("unable to send notifications", exc_info=e)
            return await expo_push(headers, data, attempts=attempts)


async def handle_expo_response(json_resp):
    tickets = json_resp.get("data")

    ok_messages = 0
    error_messages = 0

    for index, ticket in enumerate(tickets):
        status = ticket.get("status")
        if status == "ok":
            ok_messages += 1
            continue

        error_messages += 1
        details = ticket.get("details")
        error = details.get("error")

        if error == "DeviceNotRegistered":
            error_token = details.get("expoPushToken")
            logger.debug(f"DeviceNotRegistered found, removing token {error_token}")
            await find_and_update_item(
                filters={"push_tokens": error_token}, data={"$pull": {"push_tokens": error_token}}, result_obj=User
            )
        else:
            logger.error(f"unhandled push error: {ticket}")

    # todo: according to expo's docs* we should always check the push receipts 15' after the delivery response,
    # regardless of individual ticket status. Delaying this until we have a proper task manager (e.g. celery) in place.
    # *https://docs.expo.dev/push-notifications/sending-notifications/#check-push-receipts-for-errors

    logger.debug(f"push receipts. OK: {ok_messages} | ERROR: {error_messages}")


async def send_expo_push_notifications(push_messages: List[str]):
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

    json_resp = await expo_push(headers=headers, data=compressed_data)
    await handle_expo_response(json_resp)
