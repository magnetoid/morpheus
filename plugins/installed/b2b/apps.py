from django.apps import AppConfig


class B2bConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins.installed.b2b'
    label = 'b2b'
    verbose_name = 'B2B'
