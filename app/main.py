import logging.config

import sentry_sdk
import uvicorn
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from app.config import get_settings
from app.helpers.db_utils import close_mongo_connection, connect_to_mongo, override_connect_to_mongo
from app.helpers.logconf import log_configuration
from app.middlewares import add_canonical_log_line, profile_request
from app.routers import auth, base, channels, media, messages, servers, users, webhooks, websockets

logging.config.dictConfig(log_configuration)
logger = logging.getLogger(__name__)


def get_application(testing=False):
    app_ = FastAPI(title="NewShades API", default_response_class=ORJSONResponse)

    if testing:
        app_.add_event_handler("startup", override_connect_to_mongo)
    else:
        app_.add_event_handler("startup", connect_to_mongo)

    app_.add_event_handler("shutdown", close_mongo_connection)

    origins = ["*"]  # TODO: change this later

    app_.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    settings = get_settings()

    # Force HTTPS when not testing or local
    if not settings.testing:
        app_.add_middleware(HTTPSRedirectMiddleware)

        sentry_sdk.init(dsn=settings.sentry_dsn)
        app_.add_middleware(SentryAsgiMiddleware)

    app_.add_middleware(BaseHTTPMiddleware, dispatch=add_canonical_log_line)

    if settings.profiling:
        app_.add_middleware(BaseHTTPMiddleware, dispatch=profile_request)

    app_.include_router(base.router)
    app_.include_router(auth.router, prefix="/auth", tags=["auth"])
    app_.include_router(users.router, prefix="/users", tags=["users"])
    app_.include_router(servers.router, prefix="/servers", tags=["servers"])
    app_.include_router(channels.router, prefix="/channels", tags=["channels"])
    app_.include_router(messages.router, prefix="/messages", tags=["messages"])
    app_.include_router(websockets.router, prefix="/websockets", tags=["websockets"])
    app_.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
    app_.include_router(media.router, prefix="/media", tags=["media"])

    return app_


app = get_application()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True)
