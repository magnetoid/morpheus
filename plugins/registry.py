"""
Morpheus CMS — Plugin Registry
Discovers, validates, loads, and manages the lifecycle of all plugins.
"""
import importlib
import logging
from pathlib import Path
from typing import Type

from plugins.base import MorpheusPlugin

logger = logging.getLogger('morpheus.plugins')


class PluginRegistry:
    """
    Central registry for all Morph plugins.

    Responsibilities:
    - Discover plugin classes from plugins/installed/
    - Validate dependency graph
    - Two-tier activation: INSTALLED_APPS (models) + behavioral (hooks/URLs/GQL)
    - Aggregate GraphQL extensions for schema assembly
    - Aggregate plugin URL patterns
    """

    def __init__(self):
        self._plugins: dict[str, MorpheusPlugin] = {}          # name → instance
        self._classes: dict[str, Type[MorpheusPlugin]] = {}    # name → class
        self._active: set[str] = set()                      # behaviorally active plugins
        self._graphql_extensions: list[str] = []            # module paths
        self._plugin_urls: list[dict] = []                  # {urlconf, prefix, namespace}
        self._task_modules: list[str] = []
        self._context_processors: list = []
        self._ready = False

    # ── Discovery ──────────────────────────────────────────────────────────────

    def discover(self, plugin_module_paths: list[str]) -> None:
        """
        Import each plugin module path and register the MorpheusPlugin subclass found.
        Called from settings.py before Django app registry is ready.
        """
        for module_path in plugin_module_paths:
            try:
                plugin_module_path = f"{module_path}.plugin"
                mod = importlib.import_module(plugin_module_path)
                plugin_class = self._find_plugin_class(mod, module_path)
                if plugin_class:
                    self._classes[plugin_class.name] = plugin_class
                    logger.debug(f"Discovered plugin: {plugin_class.name} ({module_path})")
            except Exception as e:
                logger.error(f"Failed to discover plugin {module_path}: {e}", exc_info=True)

    def _find_plugin_class(self, module, module_path: str) -> Type[MorpheusPlugin] | None:
        """Find the MorpheusPlugin subclass in a module."""
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if (
                isinstance(obj, type)
                and issubclass(obj, MorpheusPlugin)
                and obj is not MorpheusPlugin
                and obj.name
            ):
                return obj
        logger.warning(f"No MorpheusPlugin subclass found in {module_path}.plugin")
        return None

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """
        Validate the dependency graph of all discovered plugins.
        Returns list of error messages (empty = all good).
        """
        errors = []
        for name, cls in self._classes.items():
            for dep in cls.requires:
                if dep not in self._classes:
                    errors.append(f"Plugin '{name}' requires '{dep}' which is not installed.")
            for conflict in cls.conflicts:
                if conflict in self._classes:
                    errors.append(
                        f"Plugin '{name}' conflicts with '{conflict}' — both are installed."
                    )
        return errors

    # ── Activation ────────────────────────────────────────────────────────────

    def activate_all(self) -> None:
        """
        Behaviorally activate all plugins that are enabled in the DB.
        Called from AppConfig.ready() after Django is fully loaded.
        """
        if self._ready:
            return

        enabled_names = self._get_enabled_from_db()

        for name, cls in self._classes.items():
            instance = cls()
            instance._registry = self
            self._plugins[name] = instance

            if name in enabled_names:
                self._activate(instance)

        self._ready = True
        logger.info(f"Plugin system ready. Active: {sorted(self._active)}")

    def _activate(self, plugin: MorpheusPlugin) -> None:
        """Activate a single plugin — call ready() and mark active."""
        try:
            plugin.ready()
            self._active.add(plugin.name)
            logger.info(f"Plugin activated: {plugin.name} v{plugin.version}")
        except Exception as e:
            logger.error(f"Failed to activate plugin {plugin.name}: {e}", exc_info=True)

    def deactivate(self, name: str) -> None:
        """Deactivate a plugin — call on_disable() and update DB."""
        if name in self._plugins and name in self._active:
            self._plugins[name].on_disable()
            self._active.discard(name)
            self._update_db_status(name, enabled=False)
            logger.info(f"Plugin deactivated: {name}")

    def _get_enabled_from_db(self) -> set[str]:
        """Get set of behaviorally enabled plugin names from DB."""
        try:
            from plugins.models import PluginConfig
            return set(
                PluginConfig.objects.filter(is_enabled=True).values_list('plugin_name', flat=True)
            )
        except Exception:
            # DB not ready yet (first run) — activate all discovered plugins
            logger.warning("Could not read PluginConfig from DB — activating all discovered plugins.")
            return set(self._classes.keys())

    def _update_db_status(self, name: str, enabled: bool) -> None:
        try:
            from plugins.models import PluginConfig
            PluginConfig.objects.update_or_create(
                plugin_name=name,
                defaults={'is_enabled': enabled},
            )
        except Exception as e:
            logger.error(f"Failed to update DB status for plugin {name}: {e}")

    # ── Registration (called by plugin.ready()) ────────────────────────────────

    def add_graphql_extension(self, module: str) -> None:
        if module not in self._graphql_extensions:
            self._graphql_extensions.append(module)

    def add_plugin_urls(self, urlconf: str, prefix: str = '', namespace: str = '') -> None:
        self._plugin_urls.append({'urlconf': urlconf, 'prefix': prefix, 'namespace': namespace})

    def add_task_module(self, module: str) -> None:
        if module not in self._task_modules:
            self._task_modules.append(module)

    def add_context_processor(self, func) -> None:
        self._context_processors.append(func)

    # ── GraphQL schema assembly ────────────────────────────────────────────────

    def get_graphql_extensions(self, extension_type: str) -> list[type]:
        """
        Collect Query/Mutation mixin classes from all registered GQL modules.
        extension_type: 'query' | 'mutation'
        """
        bases = []
        attr_map = {'query': 'StorefrontQuery', 'mutation': 'StorefrontMutation'}
        for module_path in self._graphql_extensions:
            try:
                mod = importlib.import_module(module_path)
                # Plugins expose StoreQuery/StoreMutation or plugin-specific names
                for attr in dir(mod):
                    obj = getattr(mod, attr)
                    if (
                        isinstance(obj, type)
                        and attr.endswith(extension_type.capitalize() + 'Extension')
                        and obj not in bases
                    ):
                        bases.append(obj)
            except Exception as e:
                logger.error(f"Failed to load GQL extension {module_path}: {e}", exc_info=True)
        return bases

    # ── URL aggregation ───────────────────────────────────────────────────────

    def get_urlpatterns(self):
        """Return aggregated URL patterns from all active plugins."""
        from django.urls import include, path
        patterns = []
        for entry in self._plugin_urls:
            try:
                patterns.append(
                    path(
                        entry['prefix'],
                        include((entry['urlconf'], entry['namespace']))
                    )
                )
            except Exception as e:
                logger.error(f"Failed to include URLs {entry}: {e}")
        return patterns

    # ── Accessors ─────────────────────────────────────────────────────────────

    def get(self, name: str) -> MorpheusPlugin | None:
        return self._plugins.get(name)

    def is_active(self, name: str) -> bool:
        return name in self._active

    def all_plugins(self) -> list[MorpheusPlugin]:
        return list(self._plugins.values())

    def active_plugins(self) -> list[MorpheusPlugin]:
        return [p for p in self._plugins.values() if p.name in self._active]

    def __repr__(self):
        return f"<PluginRegistry: {len(self._plugins)} plugins, {len(self._active)} active>"


# Global singleton
plugin_registry = PluginRegistry()
