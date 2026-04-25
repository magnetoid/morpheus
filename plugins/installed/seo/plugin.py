"""SEO plugin manifest."""
from __future__ import annotations

import logging

from core.hooks import MorpheusEvents
from plugins.base import MorpheusPlugin

logger = logging.getLogger('morpheus.seo')


class SeoPlugin(MorpheusPlugin):
    name = 'seo'
    label = 'SEO'
    version = '0.1.0'
    description = (
        'Per-object meta + JSON-LD, sitemap.xml, robots.txt, redirects, '
        'and AI-driven autofill on product create.'
    )
    has_models = True

    def ready(self) -> None:
        self.register_graphql_extension('plugins.installed.seo.graphql.queries')
        self.register_graphql_extension('plugins.installed.seo.graphql.mutations')
        self.register_urls('plugins.installed.seo.urls', prefix='', namespace='seo')
        self.register_hook(MorpheusEvents.PRODUCT_CREATED, self.on_product_created, priority=85)

    def on_product_created(self, product, **kwargs):
        try:
            from plugins.installed.seo.services import autofill_meta_for
            autofill_meta_for(product)
        except Exception as e:  # noqa: BLE001 — autofill is best-effort
            logger.warning('seo: autofill failed for product %s: %s', product.id, e, exc_info=True)
