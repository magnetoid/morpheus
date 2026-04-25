"""Affiliates plugin manifest."""
from __future__ import annotations

from core.hooks import MorpheusEvents
from plugins.base import MorpheusPlugin


class AffiliatesPlugin(MorpheusPlugin):
    name = 'affiliates'
    label = 'Affiliate Platform'
    version = '0.1.0'
    description = 'Affiliate links, attribution, conversions, payouts.'
    has_models = True
    requires = ['orders', 'customers']

    def ready(self) -> None:
        self.register_graphql_extension('plugins.installed.affiliates.graphql.queries')
        self.register_urls('plugins.installed.affiliates.urls', prefix='', namespace='affiliates')
        self.register_hook(MorpheusEvents.ORDER_PLACED, self.on_order_placed, priority=70)

    def on_order_placed(self, order, **kwargs):
        """If the order carries an affiliate code on its source/metadata, attribute it."""
        code = ''
        # Storefront writes the code into staff_notes or shipping_address.affiliate_code
        if getattr(order, 'shipping_address', None):
            code = order.shipping_address.get('affiliate_code', '') if isinstance(order.shipping_address, dict) else ''
        if not code and getattr(order, 'source', '').startswith('affiliate:'):
            code = order.source.split(':', 1)[1]
        if not code:
            return
        from plugins.installed.affiliates.services import attribute_order
        attribute_order(order=order, affiliate_code=code)
