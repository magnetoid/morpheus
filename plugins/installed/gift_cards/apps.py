from django.apps import AppConfig


class GiftCardsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins.installed.gift_cards'
    label = 'gift_cards'
    verbose_name = 'Gift Cards'
