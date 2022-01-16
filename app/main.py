import uvicorn
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from starlette.middleware.cors import CORSMiddleware

from app.routers import servers, base, auth, users


def get_application():
    app_ = FastAPI(title="NewShades API", default_response_class=ORJSONResponse)

    origins = [
        "*"  # TODO: change this later
    ]

    app_.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app_.include_router(base.router)
    app_.include_router(auth.router, prefix="/auth", tags=["auth"])
    app_.include_router(servers.router, prefix="/servers", tags=["servers"])
    app_.include_router(users.router, prefix="/users", tags=["users"])

    return app_


app = get_application()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True)
