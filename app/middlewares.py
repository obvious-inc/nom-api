import logging
import time
import uuid
from contextvars import ContextVar

import arrow
from pyinstrument import Profiler
from starlette.requests import Request

from app.config import get_settings

logger = logging.getLogger(__name__)

_request_id_ctx_var: ContextVar[str] = ContextVar("request_id")


def get_request_id() -> str:
    return _request_id_ctx_var.get()


async def profile_request(request: Request, call_next):
    settings = get_settings()

    profiler = Profiler(async_mode="enabled")
    profiler.start()
    start = time.perf_counter()

    response = await call_next(request)

    profiler.stop()
    profiler.print()

    if settings.profiling_json:
        end = time.perf_counter()
        ms = (end - start) * 1_000
        output_html = profiler.output_html(timeline=True)
        profile_file_name = (
            f"{arrow.now().timestamp()}_{ms:.2f}_{request.method}_{request.url.path[1:].replace('/', '-')}"
        )
        with open(f"{profile_file_name}.html", "w") as f:
            f.write(output_html)

    return response


async def add_canonical_log_line(request: Request, call_next):
    start_time = time.time()

    # heroku has their own request id. use that if available
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4()
    request_id = _request_id_ctx_var.set(str(request_id))
    request.state.request_id = request_id

    logger.info("%s %s", request.method, request.url.path)

    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = "{:.2f}".format(process_time)

    log_line_data = {
        "duration": formatted_process_time,
        "http_method": request.method,
        "http_path": request.url.path,
        "http_status": response.status_code,
    }

    for attr in ["user_id", "auth_type", "auth_source", "actor_type", "app_id"]:
        try:
            log_line_data[attr] = getattr(request.state, attr)
        except AttributeError:
            pass

    sorted_dict = dict(sorted(log_line_data.items(), key=lambda x: x[0].lower()))

    log_line = " ".join([f"{key}={value}" for key, value in sorted_dict.items()])
    logger.info("canonical-log %s", log_line)

    _request_id_ctx_var.reset(request_id)
    return response
