import uvicorn
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from app.routers import servers, base, auth


def get_application():
    app_ = FastAPI(title="NewShades API", default_response_class=ORJSONResponse)

    app_.include_router(base.router)
    app_.include_router(auth.router, prefix="/auth", tags=["auth"])
    app_.include_router(servers.router, prefix="/servers", tags=["servers"])

    return app_


app = get_application()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True)
