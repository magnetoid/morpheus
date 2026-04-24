from django.apps import AppConfig

class MarketingConfig(AppConfig):
    name = 'plugins.installed.marketing'
    label = 'marketing'
    verbose_name = 'Marketing'

    def ready(self):
        from plugins.registry import plugin_registry
        from plugins.installed.marketing.plugin import MarketingPlugin
        if 'marketing' not in plugin_registry._classes:
            plugin_registry._classes['marketing'] = MarketingPlugin

default_app_config = 'plugins.installed.marketing.apps.MarketingConfig'
