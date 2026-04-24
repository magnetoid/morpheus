"""Plugin context processor — exposes active plugins to templates."""


def plugin_context(request):
    from plugins.registry import plugin_registry
    return {
        'active_plugins': plugin_registry._active,
        'plugin_registry': plugin_registry,
    }
