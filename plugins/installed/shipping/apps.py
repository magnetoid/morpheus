from django.apps import AppConfig


class ShippingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins.installed.shipping'
    label = 'shipping'
    verbose_name = 'Shipping'
