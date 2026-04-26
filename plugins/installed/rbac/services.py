"""RBAC services."""
from __future__ import annotations

import logging
from typing import Iterable

logger = logging.getLogger('morpheus.rbac')


def has_capability(user, capability: str, *, channel=None) -> bool:
    """True if `user` is granted `capability` (optionally on `channel`).

    - Superusers always pass.
    - Channel-bound role: matches when binding.channel == channel OR binding.channel IS NULL.
    """
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    from plugins.installed.rbac.models import RoleBinding
    qs = RoleBinding.objects.filter(user=user).select_related('role')
    if channel is not None:
        from django.db.models import Q
        qs = qs.filter(Q(channel=channel) | Q(channel__isnull=True))
    for binding in qs:
        if capability in (binding.role.capabilities or []):
            return True
    return False


def capabilities_for(user, *, channel=None) -> set[str]:
    """The full set of capabilities `user` has — useful for menu visibility."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return set()
    if getattr(user, 'is_superuser', False):
        return {'__all__'}
    from plugins.installed.rbac.models import RoleBinding
    qs = RoleBinding.objects.filter(user=user).select_related('role')
    if channel is not None:
        from django.db.models import Q
        qs = qs.filter(Q(channel=channel) | Q(channel__isnull=True))
    out: set[str] = set()
    for binding in qs:
        for cap in (binding.role.capabilities or []):
            out.add(cap)
    return out


def grant(user, role_slug: str, *, channel=None, granted_by=None) -> 'RoleBinding | None':  # noqa: F821
    from plugins.installed.rbac.models import Role, RoleBinding
    role = Role.objects.filter(slug=role_slug).first()
    if not role:
        logger.warning('rbac: unknown role %s', role_slug)
        return None
    binding, _ = RoleBinding.objects.get_or_create(
        user=user, role=role, channel=channel,
        defaults={'granted_by': granted_by},
    )
    return binding


def revoke(user, role_slug: str, *, channel=None) -> int:
    from plugins.installed.rbac.models import RoleBinding
    n, _ = RoleBinding.objects.filter(
        user=user, role__slug=role_slug, channel=channel,
    ).delete()
    return n
