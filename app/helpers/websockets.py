import os

import pusher
from dotenv import load_dotenv
from pusher.aiohttp import AsyncIOBackend

load_dotenv()

# TODO: this kind of breaks away from FastAPI's default way of initializing 3rd party clients using dependencies,
#  but I couldn't find a straightforward way to initialize this once, and not per request. The startup events felt
#  more hacky than anything else, but might be worth another look.
pusher_client = pusher.Pusher(
    app_id=os.getenv("PUSHER_APP_ID"),
    key=os.getenv("PUSHER_KEY"),
    secret=os.getenv("PUSHER_SECRET"),
    cluster=os.getenv("PUSHER_CLUSTER"),
    backend=AsyncIOBackend,
    ssl=True,
)
