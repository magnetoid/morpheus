from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = 'plugins.installed.catalog'
    label = 'catalog'
    verbose_name = 'Catalog'

    def ready(self):
        from plugins.registry import plugin_registry
        from plugins.installed.catalog.plugin import CatalogPlugin
        import plugins.installed.catalog.signals
        if 'catalog' not in plugin_registry._classes:
            plugin_registry._classes['catalog'] = CatalogPlugin
