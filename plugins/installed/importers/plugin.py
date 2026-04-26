"""Importer plugin manifest."""
from __future__ import annotations

from plugins.base import MorpheusPlugin
from plugins.contributions import DashboardPage


class ImportersPlugin(MorpheusPlugin):
    name = 'importers'
    label = 'Migration Importers'
    version = '0.2.0'
    description = (
        'Idempotent importers: Shopify, WooCommerce, Magento, BigCommerce, '
        'plus bulk CSV products import/export.'
    )
    has_models = True

    def ready(self) -> None:
        self.register_urls(
            'plugins.installed.importers.urls',
            prefix='dashboard/import/',
            namespace='importers',
        )

    def contribute_dashboard_pages(self) -> list:
        return [
            DashboardPage(
                slug='import-csv',
                label='Bulk CSV',
                section='Catalog',
                icon='upload',
                url='/dashboard/import/csv/',
                description='Import or export products as CSV.',
            ),
        ]
