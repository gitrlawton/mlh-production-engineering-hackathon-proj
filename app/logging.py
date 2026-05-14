import logging
from collections import deque
from datetime import datetime

MAX_LOG_ENTRIES = 1000

_log_buffer = deque(maxlen=MAX_LOG_ENTRIES)


class BufferHandler(logging.Handler):
    def emit(self, record):
        _log_buffer.append({
            "timestamp": datetime.fromtimestamp(record.created).strftime("%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "message": record.getMessage(),
        })


def get_log_buffer():
    return _log_buffer


def init_logging(app):
    handler = BufferHandler()
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
