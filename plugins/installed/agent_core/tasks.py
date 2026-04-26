"""Celery tasks for the agent kernel layer."""
from __future__ import annotations

from celery import shared_task

from plugins.installed.agent_core.scheduler import tick


@shared_task(bind=True, time_limit=600, soft_time_limit=540)
def background_agents_tick(self) -> int:
    """Run every active BackgroundAgent whose next_run_at <= now."""
    return tick()
