import uvicorn
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from app.config import get_settings
from app.routers import auth, base, channels, messages, servers, users, webhooks, websockets


def get_application():
    app_ = FastAPI(title="NewShades API", default_response_class=ORJSONResponse)

    origins = ["*"]  # TODO: change this later

    app_.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app_.include_router(base.router)
    app_.include_router(auth.router, prefix="/auth", tags=["auth"])
    app_.include_router(users.router, prefix="/users", tags=["users"])
    app_.include_router(servers.router, prefix="/servers", tags=["servers"])
    app_.include_router(channels.router, prefix="/channels", tags=["channels"])
    app_.include_router(messages.router, prefix="/messages", tags=["messages"])
    app_.include_router(websockets.router, prefix="/websockets", tags=["websockets"])
    app_.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

    settings = get_settings()

    # Force HTTPS when not testing or local
    if not settings.testing:
        app_.add_middleware(HTTPSRedirectMiddleware)

    return app_


app = get_application()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True)
