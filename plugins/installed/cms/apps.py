from django.apps import AppConfig


class CmsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins.installed.cms'
    label = 'cms'
    verbose_name = 'CMS'
