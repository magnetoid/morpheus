"""Analytics tasks — fire-and-forget event logging.

Stub implementation: the analytics plugin currently has no `AnalyticsEvent`
model wired (a richer rewrite is in the standing queue). Until then the
task accepts events and drops them silently so the hook fan-out doesn't
log a stack trace on every event.
"""
from __future__ import annotations

import logging

from morph.celery import app

logger = logging.getLogger('morpheus.analytics')


@app.task(name='analytics.log_event', ignore_result=True, time_limit=20, soft_time_limit=10)
def log_analytics_event(payload):
    """Accept an event payload. No-op until the AnalyticsEvent model lands."""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('analytics: dropped event (no model wired): %s', payload)
