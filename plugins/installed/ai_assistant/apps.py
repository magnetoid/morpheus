from django.apps import AppConfig

class AIAssistantConfig(AppConfig):
    name = 'plugins.installed.ai_assistant'
    label = 'ai_assistant'
    verbose_name = 'AI Assistant'

    def ready(self):
        from plugins.registry import plugin_registry
        from plugins.installed.ai_assistant.plugin import AIAssistantPlugin
        if 'ai_assistant' not in plugin_registry._classes:
            plugin_registry._classes['ai_assistant'] = AIAssistantPlugin

default_app_config = 'plugins.installed.ai_assistant.apps.AIAssistantConfig'
