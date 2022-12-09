import asyncio
import logging
import sys

from asgi_lifespan import LifespanManager

from app.helpers.whitelist import whitelist_wallet
from app.main import get_application

logger = logging.getLogger(__name__)


async def main():
    app = get_application()
    async with LifespanManager(app):
        wallet_address = sys.argv[1] or None
        try:
            await whitelist_wallet(wallet_address)
        except Exception as e:
            logger.warning(f"problem whitelisting address {wallet_address}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
