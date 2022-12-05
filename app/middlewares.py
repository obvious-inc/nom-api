import logging
import time
import uuid
from contextvars import ContextVar
from typing import Dict, Optional

import arrow
from pyinstrument import Profiler
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

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


class CanonicalLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        instance: Dict[str, Optional[int]] = {"http_status_code": None}

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        def send_wrapper(response):
            if response["type"] == "http.response.start":
                instance["http_status_code"] = response["status"]
            return send(response)

        start_time = time.time()

        request = Request(scope)
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4()
        request_id = _request_id_ctx_var.set(str(request_id))
        request.state.request_id = request_id

        logger.info("%s %s", request.method, request.url.path)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            instance["http_status_code"] = 500
            raise exc
        finally:
            process_time = (time.time() - start_time) * 1000
            formatted_process_time = "{:.2f}".format(process_time)

            log_line_data = {
                "duration": formatted_process_time,
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": instance["http_status_code"],
                "type": "request",
            }

            for attr in ["user_id", "auth_type", "auth_source", "actor_type", "app_id", "permissions_used"]:
                try:
                    log_line_data[attr] = getattr(request.state, attr)
                except AttributeError:
                    pass

            sorted_dict = dict(sorted(log_line_data.items(), key=lambda x: x[0].lower()))

            log_line = " ".join([f"{key}={value}" for key, value in sorted_dict.items()])
            logger.info("canonical-log %s", log_line)

            _request_id_ctx_var.reset(request_id)
