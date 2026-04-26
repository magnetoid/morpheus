"""Tax services — compute tax for a cart given an address."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Iterable

from djmoney.money import Money

logger = logging.getLogger('morpheus.tax')


def _resolve_region(country: str, region: str) -> 'TaxRegion | None':  # noqa: F821
    """Find the most specific matching region, falling back to country-only."""
    from plugins.installed.tax.models import TaxConfiguration, TaxRegion

    country = (country or '').strip().upper()[:2]
    region = (region or '').strip().upper()[:10]
    if not country:
        config = TaxConfiguration.objects.first()
        return config.default_region if config else None

    if region:
        match = TaxRegion.objects.filter(country=country, region=region).first()
        if match:
            return match
    return TaxRegion.objects.filter(country=country, region='').first()


def _resolve_rate(region, category_code: str) -> 'TaxRate | None':  # noqa: F821
    from plugins.installed.tax.models import TaxRate

    qs = TaxRate.objects.filter(region=region)
    if category_code:
        cat = qs.filter(category_id=category_code).first()
        if cat:
            return cat
    return qs.filter(category__isnull=True).first()


def compute_tax(*, line_items: Iterable[dict], country: str = '', region: str = '') -> dict:
    """Compute tax for a list of line items.

    Each line item: {'amount': Decimal|str, 'currency': str, 'category_code': str (optional)}.
    Returns: {'total': Money, 'lines': [{'rate_name', 'rate_percent', 'amount': Money}]}.
    """
    from plugins.installed.tax.models import TaxConfiguration

    config = TaxConfiguration.objects.first()
    if config and config.provider == 'none':
        return {'total': None, 'lines': []}

    tax_region = _resolve_region(country, region)
    if not tax_region:
        return {'total': None, 'lines': []}

    by_rate: dict[str, dict] = {}
    currency: str | None = None
    for item in line_items:
        amount = Decimal(str(item.get('amount', 0)))
        currency = currency or item.get('currency') or 'USD'
        rate = _resolve_rate(tax_region, item.get('category_code', ''))
        if rate is None or amount <= 0:
            continue
        tax_amt = (amount * rate.fraction).quantize(Decimal('0.01'))
        existing = by_rate.setdefault(str(rate.id), {
            'rate_name': rate.name, 'rate_percent': str(rate.rate_percent),
            'amount': Decimal('0'),
        })
        existing['amount'] += tax_amt

    lines = []
    total = Decimal('0')
    for v in by_rate.values():
        amt = v['amount'].quantize(Decimal('0.01'))
        total += amt
        lines.append({
            'rate_name': v['rate_name'],
            'rate_percent': v['rate_percent'],
            'amount': Money(amt, currency or 'USD'),
        })
    return {
        'total': Money(total.quantize(Decimal('0.01')), currency or 'USD') if total > 0 else None,
        'lines': lines,
    }


def compute_tax_for_cart(cart, *, country: str = '', region: str = '') -> dict:
    """Convenience wrapper: pull line items off a Cart."""
    items = []
    for item in cart.items.select_related('product').all():
        category_code = ''
        product = item.product
        if hasattr(product, 'tax_category_code'):
            category_code = getattr(product, 'tax_category_code', '') or ''
        amount = Decimal(item.unit_price.amount) * item.quantity
        items.append({
            'amount': amount,
            'currency': str(item.unit_price.currency),
            'category_code': category_code,
        })
    return compute_tax(line_items=items, country=country, region=region)
