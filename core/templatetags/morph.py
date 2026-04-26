"""Core Morpheus template tags.

Exposes one tag — `{% storefront_blocks "slot_name" %}` — which renders
every plugin contribution registered against that slot, in priority
order. Themes use this to give plugins a place to draw on the
storefront without any plugin needing to monkey-patch templates.

Usage:

    {% load morph %}
    <main>
      ...
      {% storefront_blocks "home_below_grid" %}
      ...
    </main>
"""
from __future__ import annotations

import logging

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

logger = logging.getLogger('morpheus.templatetags')

register = template.Library()


@register.simple_tag(takes_context=True)
def storefront_blocks(context, slot: str) -> str:
    """Render every storefront block contributed for `slot`."""
    if not slot:
        return ''
    try:
        from plugins.registry import plugin_registry
    except ImportError:
        return ''

    blocks = plugin_registry.storefront_blocks_for(slot)
    if not blocks:
        return ''

    rendered_parts: list[str] = []
    request = context.get('request')
    base_ctx = {k: v for k, v in context.flatten().items() if k != 'block'}

    for block in blocks:
        try:
            rendered_parts.append(
                render_to_string(block.template, {**base_ctx, 'block': block}, request=request)
            )
        except Exception as e:  # noqa: BLE001 — never break the page on a bad block
            logger.warning(
                'storefront_blocks: %s/%s render failed: %s',
                block.plugin, block.slot, e, exc_info=True,
            )
    return mark_safe(''.join(rendered_parts))


@register.filter(name='convert')
def convert_money(value, target_currency: str):
    """Convert a Money value to the target currency using the latest ExchangeRate.

    No-op (returns value as-is) when:
    - value isn't a Money object,
    - source and target currencies match,
    - no ExchangeRate row exists for the pair.
    """
    if not value or not target_currency:
        return value
    try:
        from djmoney.money import Money
        from core.models import ExchangeRate
    except ImportError:
        return value
    if not isinstance(value, Money):
        return value
    src = str(value.currency)
    tgt = (target_currency or '').upper()[:3]
    if src == tgt:
        return value
    try:
        rate = ExchangeRate.objects.filter(base_currency=src, quote_currency=tgt).first()
    except Exception:  # noqa: BLE001
        return value
    if rate is None:
        return value
    from decimal import Decimal
    converted = (Decimal(value.amount) * Decimal(rate.rate)).quantize(Decimal('0.01'))
    return Money(converted, tgt)
