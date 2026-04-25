"""Plugin context processor — exposes active plugins + dashboard contributions."""
from __future__ import annotations


def plugin_context(request):
    from plugins.registry import plugin_registry

    return {
        'active_plugins': plugin_registry._active,
        'plugin_registry': plugin_registry,
        # Pre-flattened for the dashboard sidebar; cheap because the registry
        # already keeps these sorted at activation time.
        'dashboard_pages': plugin_registry.dashboard_pages(),
    }
