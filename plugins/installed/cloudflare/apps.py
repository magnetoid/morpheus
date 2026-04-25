from django.apps import AppConfig


class CloudflareConfig(AppConfig):
    name = 'plugins.installed.cloudflare'
    label = 'cloudflare'
    default_auto_field = 'django.db.models.BigAutoField'
