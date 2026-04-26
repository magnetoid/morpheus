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


def healthz_deep(request: HttpRequest) -> JsonResponse:
    """Deep health — DB + cache + plugin registry + agent runtime + outbox lag."""
    checks: dict[str, dict] = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        checks['db'] = {'ok': True}
    except DatabaseError as e:
        checks['db'] = {'ok': False, 'error': str(e)[:200]}

    try:
        cache.set('morpheus:hzdeep', '1', timeout=10)
        checks['cache'] = {'ok': cache.get('morpheus:hzdeep') == '1'}
    except Exception as e:  # noqa: BLE001
        checks['cache'] = {'ok': False, 'error': str(e)[:200]}

    try:
        from plugins.registry import plugin_registry
        active = list(plugin_registry._active)
        checks['plugins'] = {'ok': True, 'active_count': len(active)}
    except Exception as e:  # noqa: BLE001
        checks['plugins'] = {'ok': False, 'error': str(e)[:200]}

    try:
        from core.agents import agent_registry
        checks['agents'] = {
            'ok': True,
            'agents': len(agent_registry.all_agents()),
            'tools': len(agent_registry.platform_tools()),
        }
    except Exception as e:  # noqa: BLE001
        checks['agents'] = {'ok': False, 'error': str(e)[:200]}

    try:
        from core.assistant.providers import get_default_provider
        provider = get_default_provider()
        checks['assistant'] = {'ok': True, 'provider': provider.name, 'model': provider.model}
    except Exception as e:  # noqa: BLE001
        checks['assistant'] = {'ok': False, 'error': str(e)[:200]}

    try:
        from core.models import OutboxEvent
        unsent = OutboxEvent.objects.filter(sent_at__isnull=True).count()
        checks['outbox'] = {'ok': unsent < 1000, 'unsent': unsent}
    except Exception as e:  # noqa: BLE001
        checks['outbox'] = {'ok': True, 'note': 'unavailable'}

    ok = all(c.get('ok', False) for c in checks.values())
    return JsonResponse(
        {'status': 'ok' if ok else 'degraded', 'checks': checks},
        status=200 if ok else 503,
    )
