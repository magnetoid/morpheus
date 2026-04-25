"""
Morpheus CMS — Celery Configuration.

Wires the Celery app to Django settings, hooks OpenTelemetry + Sentry, and
captures every task failure into the observability ErrorEvent table so the
merchant dashboard can see them.
"""
from __future__ import annotations

import logging
import os

from celery import Celery
from celery.signals import task_failure

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'morph.settings')

logger = logging.getLogger('morpheus.celery')

app = Celery('morpheus')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Observability bootstrap — fail-soft: missing OTel deps must not break workers.
try:
    from core.observability import init_observability
    init_observability()
except Exception as e:  # noqa: BLE001
    logger.debug('celery: observability init skipped: %s', e)

try:
    from core.sentry import init_sentry
    init_sentry()
except Exception as e:  # noqa: BLE001
    logger.debug('celery: sentry init skipped: %s', e)


@task_failure.connect
def _on_task_failure(sender=None, task_id=None, exception=None,
                     traceback=None, einfo=None, **kwargs):
    """Persist task failures into the ErrorEvent table + Redis deadletter."""
    msg = str(exception)[:5000]
    stack = (str(einfo) if einfo else '')[:20000]
    try:
        from plugins.installed.observability.services import record_error
        record_error(
            source='celery',
            message=msg,
            stack_trace=stack,
            metadata={
                'task': sender.name if sender else '',
                'task_id': task_id or '',
                'exc_type': type(exception).__name__ if exception else '',
            },
        )
    except Exception as e:  # noqa: BLE001 — observability outage must not block worker
        logger.debug('celery: failed to record_error: %s', e)

    try:
        from django.core.cache import cache
        cache.set(
            f'morpheus:deadletter:{task_id}',
            {'task': sender.name if sender else '', 'message': msg, 'stack': stack[:2000]},
            timeout=60 * 60 * 24 * 7,
        )
    except Exception as e:  # noqa: BLE001 — cache outage must not block worker
        logger.debug('celery: failed to write deadletter: %s', e)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
