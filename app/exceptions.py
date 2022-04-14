import logging

import marshmallow
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


async def assertion_exception_handler(request: Request, exc: AssertionError):
    logger.warning(f"marshmallow validation error: {exc}")
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Problem with validating request"})


async def marshmallow_validation_error_handler(request: Request, exc: marshmallow.exceptions.ValidationError):
    logger.warning(f"marshmallow validation error: {exc.messages}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Problem validating data in request"}
    )


async def type_error_handler(request: Request, exc: TypeError):
    logger.warning(f"marshmallow validation error: {exc}")
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Problem with request data"})
