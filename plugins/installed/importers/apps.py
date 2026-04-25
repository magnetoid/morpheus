from django.apps import AppConfig


class ImportersConfig(AppConfig):
    name = 'plugins.installed.importers'
    label = 'importers'
    default_auto_field = 'django.db.models.BigAutoField'
