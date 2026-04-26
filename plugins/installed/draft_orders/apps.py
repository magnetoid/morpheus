from django.apps import AppConfig


class DraftOrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins.installed.draft_orders'
    label = 'draft_orders'
    verbose_name = 'Draft Orders'
