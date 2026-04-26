from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.audit'
    label = 'morph_audit'
    verbose_name = 'Morpheus audit log'
