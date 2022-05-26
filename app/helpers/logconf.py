import logging

from app.middlewares import get_request_id


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        try:
            record.request_id = get_request_id()
        except Exception:
            record.request_id = None
        return True


log_configuration = {
    "version": 1,
    "formatters": {
        "default": {
            "class": "logging.Formatter",
            "format": "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
        },
        "normal": {
            "class": "logging.Formatter",
            "format": "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s request_id=%(request_id)s",
        },
    },
    "filters": {
        "request_id": {
            "()": RequestIDFilter,
        }
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "app": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "normal",
            "stream": "ext://sys.stdout",
            "filters": ["request_id"],
        },
    },
    "loggers": {
        "app": {"handlers": ["app"], "level": "DEBUG", "propagate": False},
        "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "gql": {"handlers": ["default"], "level": "WARNING", "propagate": False},
    },
    "root": {"level": "INFO", "handlers": ["default"]},
    "disable_existing_loggers": False,
}
