"""JSON log formatter for production. One line per record, machine-friendly."""
from __future__ import annotations

import json
import logging
import time
import traceback


_RESERVED = {
    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
    'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
    'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
    'processName', 'process', 'message', 'asctime',
}


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON object.

    Includes `request_id` (from the request_id filter), `level`, `logger`,
    `module`, and any structured fields the caller passed via `extra=`.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            'ts': time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(record.created)) + f'.{int(record.msecs):03d}Z',
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'msg': record.getMessage(),
            'request_id': getattr(record, 'request_id', '-'),
        }
        # Surface any extra= fields without leaking the LogRecord internals.
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith('_'):
                continue
            if key in payload:
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)

        if record.exc_info:
            payload['exc'] = ''.join(traceback.format_exception(*record.exc_info)).rstrip()

        return json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
