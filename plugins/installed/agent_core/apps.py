from django.apps import AppConfig


class AgentCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins.installed.agent_core'
    label = 'agent_core'
    verbose_name = 'Agent Core'
