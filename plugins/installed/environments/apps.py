from django.apps import AppConfig


class EnvironmentsConfig(AppConfig):
    name = 'plugins.installed.environments'
    label = 'environments'
    default_auto_field = 'django.db.models.BigAutoField'
