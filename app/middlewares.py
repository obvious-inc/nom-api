import logging
import time
import uuid
from contextvars import ContextVar

from starlette.requests import Request

logger = logging.getLogger(__name__)

_request_id_ctx_var: ContextVar[str] = ContextVar("request_id")


def get_request_id() -> str:
    return _request_id_ctx_var.get()


async def add_canonical_log_line(request: Request, call_next):

    start_time = time.time()

    # heroku has their own request id. use that if available
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4()
    request_id = _request_id_ctx_var.set(request_id)

    request.state.request_id = request_id

    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = "{0:.2f}".format(process_time)

    log_line_data = {
        "duration": formatted_process_time,
        "http_method": request.method,
        "http_path": request.url.path,
        "http_status": response.status_code,
    }

    try:
        log_line_data["user_id"] = request.state.user_id
    except AttributeError:
        pass

    try:
        log_line_data["auth_type"] = request.state.auth_type
    except AttributeError:
        pass

    sorted_dict = dict(sorted(log_line_data.items(), key=lambda x: x[0].lower()))

    log_line = " ".join([f"{key}={value}" for key, value in sorted_dict.items()])
    logger.info(f"canonical-log {log_line}")

    _request_id_ctx_var.reset(request_id)
    return response
