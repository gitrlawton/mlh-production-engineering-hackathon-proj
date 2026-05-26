from collections import deque

_request_window = deque(maxlen=100)


def record_request(status_code):
    _request_window.append(status_code >= 500)


def get_error_rate():
    if not _request_window:
        return 0.0
    return round((sum(_request_window) / len(_request_window)) * 100, 1)


def get_request_window():
    return _request_window
