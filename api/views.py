from __future__ import annotations

import logging

from django.core.cache import cache
from django.core.cache.backends.base import CacheKeyWarning
from django.db import DatabaseError, connection
from django.http import HttpRequest, JsonResponse

logger = logging.getLogger('morpheus.api.health')


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness — process is up and able to respond."""
    return JsonResponse({'status': 'ok'})


def readyz(request: HttpRequest) -> JsonResponse:
    """Readiness — DB and cache are reachable."""
    checks = {'db': False, 'cache': False}

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        checks['db'] = True
    except DatabaseError as e:
        logger.warning("readyz: db check failed: %s", e)

    try:
        cache.get('morpheus:readyz')
        checks['cache'] = True
    except (ConnectionError, OSError, CacheKeyWarning) as e:
        logger.warning("readyz: cache check failed: %s", e)
    except Exception as e:  # noqa: BLE001 — backend-specific errors logged, returns degraded
        logger.warning("readyz: cache check failed: %s", e)

    ok = all(checks.values())
    return JsonResponse(
        {'status': 'ok' if ok else 'degraded', 'checks': checks},
        status=200 if ok else 503,
    )
