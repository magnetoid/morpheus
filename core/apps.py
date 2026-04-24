from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from core.utils.cache import SmartCacheInvalidator
        SmartCacheInvalidator.bind_events()
