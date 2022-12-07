import asyncio
import sys

from asgi_lifespan import LifespanManager

from app.helpers.whitelist import whitelist_wallet
from app.main import get_application


async def main():
    app = get_application()
    async with LifespanManager(app):
        wallet_address = sys.argv[1]
        await whitelist_wallet(wallet_address)


if __name__ == "__main__":
    asyncio.run(main())
