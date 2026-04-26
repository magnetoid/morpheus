from django.apps import AppConfig


class WebhooksUiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins.installed.webhooks_ui'
    label = 'webhooks_ui'
    verbose_name = 'Webhooks UI'
