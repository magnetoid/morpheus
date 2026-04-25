from __future__ import annotations

from celery import shared_task

from plugins.installed.observability.services import rollup


@shared_task(bind=True, time_limit=180, soft_time_limit=150)
def rollup_metrics(self, granularity: str = 'hour', lookback_hours: int = 6) -> int:
    return rollup(granularity=granularity, lookback_hours=lookback_hours)
