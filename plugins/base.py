"""
Morpheus CMS — MorpheusPlugin Base Class
Every plugin subclasses this.
"""
import logging
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from plugins.registry import PluginRegistry

logger = logging.getLogger('morpheus.plugins')


class MorpheusPlugin:
    """
    Base class for all Morph plugins.

    Subclass this in your plugin's plugin.py:

        class CatalogPlugin(MorpheusPlugin):
            name = "catalog"
            label = "Product Catalog"
            version = "1.0.0"
            has_models = True

            def ready(self):
                self.register_graphql_extension('plugins.installed.catalog.graphql')
                self.register_hook('order.placed', self.on_order_placed)
    """

    # ── Required metadata ──────────────────────────────────────────────────────
    name: str = ''          # unique snake_case — must match directory name
    label: str = ''         # human-readable name
    version: str = '1.0.0'
    description: str = ''
    author: str = 'Morph Team'
    url: str = ''           # plugin homepage / docs

    # ── Dependency graph ───────────────────────────────────────────────────────
    requires: list[str] = []    # other plugin names this depends on
    conflicts: list[str] = []   # plugins this cannot coexist with

    # ── Model flag ────────────────────────────────────────────────────────────
    has_models: bool = False    # True if plugin defines Django models
    # If True, plugin MUST be in INSTALLED_APPS (Tier 1 activation)

    # ── Internal ──────────────────────────────────────────────────────────────
    _registry: 'PluginRegistry | None' = None
    _config_cache: dict | None = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.name:
            raise TypeError(f"{cls.__name__} must define a 'name' attribute")

    # ── Lifecycle (override these) ─────────────────────────────────────────────

    def ready(self) -> None:
        """
        Called when plugin is behaviorally activated.
        Register hooks, URLs, GraphQL extensions, admin here.
        """
        pass

    def on_disable(self) -> None:
        """Called when plugin is behaviorally deactivated."""
        pass

    # ── Registration helpers ───────────────────────────────────────────────────

    def register_urls(self, urlconf: str, prefix: str = '', namespace: str | None = None) -> None:
        """Register URL patterns from a urlconf module."""
        if self._registry:
            self._registry.add_plugin_urls(urlconf, prefix=prefix, namespace=namespace or self.name)

    def register_graphql_extension(self, module: str) -> None:
        """Register a module containing Strawberry Query/Mutation mixins."""
        if self._registry:
            self._registry.add_graphql_extension(module)

    def register_hook(self, event: str, handler: Callable, priority: int = 50) -> None:
        """Register a hook handler via the global hook registry."""
        from core.hooks import hook_registry
        hook_registry.register(event, handler, priority=priority)

    def register_admin(self, model, admin_class) -> None:
        """Register a model with the Django admin."""
        from django.contrib import admin as django_admin
        try:
            django_admin.site.register(model, admin_class)
        except django_admin.sites.AlreadyRegistered:
            pass

    def register_celery_tasks(self, module: str) -> None:
        """Ensure Celery autodiscovers tasks from a module."""
        if self._registry:
            self._registry.add_task_module(module)

    def register_context_processor(self, func: Callable) -> None:
        """Add a template context processor."""
        if self._registry:
            self._registry.add_context_processor(func)

    # ── Configuration ──────────────────────────────────────────────────────────

    def get_config_schema(self) -> dict:
        """
        Return JSON Schema for this plugin's settings.
        Rendered as a dynamic form in the Morph admin UI.
        """
        return {}

    def get_config(self) -> dict:
        """Read current config from DB (cached)."""
        if self._config_cache is None:
            from plugins.models import PluginConfig
            try:
                row = PluginConfig.objects.get(plugin_name=self.name)
                self._config_cache = row.config
            except Exception:
                self._config_cache = {}
        return self._config_cache

    def get_config_value(self, key: str, default=None):
        """Get a single config value with fallback to schema default."""
        config = self.get_config()
        if key in config:
            return config[key]
        schema = self.get_config_schema()
        return schema.get('properties', {}).get(key, {}).get('default', default)

    def set_config(self, key: str, value) -> None:
        """Set a single config value in DB."""
        from plugins.models import PluginConfig
        row, _ = PluginConfig.objects.get_or_create(plugin_name=self.name)
        row.config[key] = value
        row.save(update_fields=['config', 'updated_at'])
        self._config_cache = None  # invalidate cache

    def invalidate_config_cache(self) -> None:
        self._config_cache = None

    # ── Info ──────────────────────────────────────────────────────────────────

    def __repr__(self):
        return f"<MorpheusPlugin: {self.name} v{self.version}>"
