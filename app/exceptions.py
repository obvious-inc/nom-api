import logging

from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


async def assertion_exception_handler(request: Request, exc: AssertionError):
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Problem with validating request"})
