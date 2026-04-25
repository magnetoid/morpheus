"""Template helpers for the advanced_ecommerce storefront blocks."""
from __future__ import annotations

from django import template

register = template.Library()


@register.simple_tag
def recently_viewed_product(slug: str):
    """Return a Product by slug or None. Used in the recently-viewed rail."""
    if not slug:
        return None
    try:
        from plugins.installed.catalog.models import Product
        return (
            Product.objects.filter(slug=slug, status='active')
            .select_related('category')
            .first()
        )
    except Exception:  # noqa: BLE001 — never break rendering
        return None


@register.simple_tag
def free_shipping_target():
    """Returns (target_amount, currency) tuple from plugin config."""
    try:
        from plugins.registry import plugin_registry
        plugin = plugin_registry.get('advanced_ecommerce')
        if plugin is None:
            return 40, 'USD'
        return (
            plugin.get_config_value('free_shipping_target', 40),
            plugin.get_config_value('free_shipping_currency', 'USD'),
        )
    except Exception:  # noqa: BLE001
        return 40, 'USD'


@register.simple_tag
def low_stock_threshold() -> int:
    try:
        from plugins.registry import plugin_registry
        plugin = plugin_registry.get('advanced_ecommerce')
        return int(plugin.get_config_value('low_stock_threshold', 5)) if plugin else 5
    except Exception:  # noqa: BLE001
        return 5


@register.simple_tag
def product_total_stock(product) -> int:
    """Sum of available stock across all variants of a product."""
    if product is None:
        return 0
    try:
        from plugins.installed.inventory.models import StockLevel
        total = 0
        for sl in StockLevel.objects.filter(variant__product=product):
            total += max(0, sl.quantity - sl.reserved_quantity)
        return total
    except Exception:  # noqa: BLE001
        return 0
