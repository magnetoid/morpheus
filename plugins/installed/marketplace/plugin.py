"""Multivendor marketplace plugin manifest."""
from __future__ import annotations

import logging

from core.hooks import MorpheusEvents
from plugins.base import MorpheusPlugin

logger = logging.getLogger('morpheus.marketplace')


class MarketplacePlugin(MorpheusPlugin):
    name = 'marketplace'
    label = 'Marketplace'
    version = '0.1.0'
    description = 'Multivendor marketplace: vendor onboarding, vendor orders, payouts.'
    has_models = True
    requires = ['catalog', 'orders']

    def ready(self) -> None:
        self.register_graphql_extension('plugins.installed.marketplace.graphql.queries')
        self.register_hook(MorpheusEvents.ORDER_PLACED, self.on_order_placed, priority=80)

    def on_order_placed(self, order, **kwargs):
        try:
            from plugins.installed.marketplace.services import split_order
            split_order(order)
        except Exception as e:  # noqa: BLE001 — never block order placement
            logger.warning('marketplace: split_order failed for %s: %s', order.id, e, exc_info=True)
