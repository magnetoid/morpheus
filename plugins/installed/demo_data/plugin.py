"""Demo data plugin manifest."""
from __future__ import annotations

from plugins.base import MorpheusPlugin
from plugins.contributions import SettingsPanel


class DemoDataPlugin(MorpheusPlugin):
    name = 'demo_data'
    label = 'Demo Data'
    version = '0.2.0'
    description = (
        'Idempotent seed data for the bookstore demo + on-demand random '
        'product generator themed by the active storefront theme. Adds '
        'a settings panel with a one-click generator.'
    )
    has_models = False
    requires_plugins: list[str] = []

    def ready(self) -> None:
        self.register_urls(
            'plugins.installed.demo_data.urls',
            prefix='dashboard/apps/demo_data/',
            namespace='demo_data',
        )

    def contribute_settings_panel(self) -> SettingsPanel:
        return SettingsPanel(
            label='Demo Data',
            description=(
                'Generate sample data on demand — products are themed by '
                'the active storefront theme.'
            ),
            schema={'type': 'object', 'properties': {}},
        )
