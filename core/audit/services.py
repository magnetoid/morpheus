"""Audit recorder — `record(...)` is the only public surface."""
from __future__ import annotations

import logging
from typing import Any, Optional

from core.utils.safe_db import safe_db

logger = logging.getLogger('morpheus.audit')


@safe_db(default=None, log_level=logging.WARNING)
def record(
    *,
    event_type: str,
    actor: Any = None,
    target: str = '',
    metadata: Optional[dict] = None,
    severity: str = 'info',
    ip_address: Optional[str] = None,
    request_id: str = '',
) -> Any:
    """Persist one audit row. Never raises (DB errors are swallowed + logged)."""
    from core.audit.models import AuditEvent

    actor_obj = actor if (actor is not None and getattr(actor, 'is_authenticated', False)) else None
    actor_label = ''
    if actor_obj is not None:
        actor_label = getattr(actor_obj, 'email', '') or getattr(actor_obj, 'username', '') or str(actor_obj.pk)
    elif actor is not None:
        actor_label = str(actor)[:200]

    return AuditEvent.objects.create(
        event_type=event_type[:120],
        severity=severity if severity in dict(AuditEvent.SEVERITY_CHOICES) else AuditEvent.SEVERITY_INFO,
        actor=actor_obj,
        actor_label=actor_label[:200],
        target=str(target)[:200] if target else '',
        metadata=metadata or {},
        ip_address=ip_address,
        request_id=request_id[:64] if request_id else '',
    )
