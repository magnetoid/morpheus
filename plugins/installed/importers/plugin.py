"""Importer plugin manifest."""
from __future__ import annotations

from plugins.base import MorpheusPlugin


class ImportersPlugin(MorpheusPlugin):
    name = 'importers'
    label = 'Migration Importers'
    version = '0.1.0'
    description = 'Idempotent importers for Shopify, WooCommerce, Magento, BigCommerce.'
    has_models = True

    def ready(self) -> None:
        # Currently CLI-only; GraphQL surface comes in a follow-up sprint.
        pass
