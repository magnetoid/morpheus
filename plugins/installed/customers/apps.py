from django.apps import AppConfig


class CustomersConfig(AppConfig):
    name = 'plugins.installed.customers'
    label = 'customers'
    verbose_name = 'Customers'

    def ready(self):
        from plugins.registry import plugin_registry
        from plugins.installed.customers.plugin import CustomersPlugin
        if 'customers' not in plugin_registry._classes:
            plugin_registry._classes['customers'] = CustomersPlugin
