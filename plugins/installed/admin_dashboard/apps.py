from django.apps import AppConfig

class AdminDashboardConfig(AppConfig):
    name = 'plugins.installed.admin_dashboard'
    label = 'admin_dashboard'
    verbose_name = 'Admin Dashboard'

    def ready(self):
        from plugins.registry import plugin_registry
        from plugins.installed.admin_dashboard.plugin import AdminDashboardPlugin
        if 'admin_dashboard' not in plugin_registry._classes:
            plugin_registry._classes['admin_dashboard'] = AdminDashboardPlugin

default_app_config = 'plugins.installed.admin_dashboard.apps.AdminDashboardConfig'
