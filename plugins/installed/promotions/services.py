"""Promotion evaluator.

Public surface:

    evaluate(cart, *, channel=None, customer=None, country=None, coupon=None)
        → list[AppliedPromotion]

Each AppliedPromotion carries the matched Promotion, the rule, the
discount amount, and a free_shipping flag. Callers (cart-total hook,
checkout, draft orders) decide how to apply.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable, Optional

from django.utils import timezone

logger = logging.getLogger('morpheus.promotions')


@dataclass
class AppliedPromotion:
    promotion_id: str
    promotion_name: str
    rule_id: Optional[str]
    discount_amount: Decimal = Decimal('0')
    free_shipping: bool = False
    gift_product_id: Optional[str] = None
    note: str = ''


def _cart_subtotal(cart) -> Decimal:
    """Best-effort subtotal extraction from arbitrary cart-like objects."""
    if cart is None:
        return Decimal('0')
    for attr in ('subtotal_amount', 'subtotal', 'total_amount', 'total'):
        v = getattr(cart, attr, None)
        if v is None:
            continue
        amount = getattr(v, 'amount', v)
        try:
            return Decimal(str(amount))
        except Exception:  # noqa: BLE001
            continue
    items = cart.get('items', []) if isinstance(cart, dict) else getattr(cart, 'items', None)
    total = Decimal('0')
    for it in (items or []):
        price = (it.get('price') if isinstance(it, dict) else getattr(it, 'price', None))
        qty = (it.get('quantity', 1) if isinstance(it, dict) else getattr(it, 'quantity', 1))
        amount = getattr(price, 'amount', price) if price is not None else 0
        try:
            total += Decimal(str(amount)) * Decimal(str(qty or 1))
        except Exception:  # noqa: BLE001
            continue
    return total


def _cart_currency(cart, default: str = 'USD') -> str:
    for attr in ('currency', 'currency_code'):
        v = getattr(cart, attr, None)
        if v:
            return str(v)
    if isinstance(cart, dict):
        return str(cart.get('currency') or default)
    return default


def _cart_product_ids(cart) -> list[str]:
    items = cart.get('items', []) if isinstance(cart, dict) else getattr(cart, 'items', None)
    out: list[str] = []
    for it in (items or []):
        if isinstance(it, dict):
            pid = it.get('product_id')
        else:
            pid = getattr(it, 'product_id', None)
            if not pid and getattr(it, 'product', None):
                pid = str(getattr(it.product, 'id', ''))
        if pid:
            out.append(str(pid))
    return out


def _matches(predicates: dict, *, cart, channel, customer, country, coupon) -> bool:
    if not predicates:
        return True
    subtotal = _cart_subtotal(cart)
    currency = _cart_currency(cart)

    if 'min_subtotal' in predicates and subtotal < Decimal(str(predicates['min_subtotal'])):
        return False
    if 'max_subtotal' in predicates and subtotal > Decimal(str(predicates['max_subtotal'])):
        return False
    if 'currencies' in predicates and currency not in predicates['currencies']:
        return False
    if 'countries' in predicates and (country or '').upper() not in [c.upper() for c in predicates['countries']]:
        return False
    if 'customer_groups' in predicates:
        groups = list(getattr(customer, 'groups', []) or [])
        if isinstance(customer, dict):
            groups = list(customer.get('groups') or [])
        if not any(g in predicates['customer_groups'] for g in (str(x) for x in groups)):
            return False
    if 'product_ids' in predicates:
        cart_pids = set(_cart_product_ids(cart))
        if not cart_pids.intersection(set(str(x) for x in predicates['product_ids'])):
            return False
    if predicates.get('first_order') and getattr(customer, 'order_count', 0) > 0:
        return False
    return True


def _apply_action(action: dict, *, subtotal: Decimal) -> tuple[Decimal, bool, Optional[str]]:
    kind = (action or {}).get('kind')
    if kind == 'percent_off':
        pct = Decimal(str(action.get('value', 0)))
        return (subtotal * pct / Decimal('100')).quantize(Decimal('0.01')), False, None
    if kind == 'fixed_off':
        return Decimal(str(action.get('value', 0))).quantize(Decimal('0.01')), False, None
    if kind == 'free_shipping':
        return Decimal('0'), True, None
    if kind == 'gift':
        return Decimal('0'), False, str(action.get('product_id') or '')
    return Decimal('0'), False, None


def evaluate(
    cart,
    *,
    channel: Any = None,
    customer: Any = None,
    country: Optional[str] = None,
    coupon: Optional[str] = None,
) -> list[AppliedPromotion]:
    from plugins.installed.promotions.models import Promotion

    now = timezone.now()
    qs = Promotion.objects.filter(is_active=True).prefetch_related('rules')
    qs = qs.filter(models_q_active(now))
    channel_slug = getattr(channel, 'slug', None) if channel is not None else None

    out: list[AppliedPromotion] = []
    subtotal = _cart_subtotal(cart)

    for promo in qs.order_by('priority'):
        if promo.channels and channel_slug and channel_slug not in promo.channels:
            continue
        if promo.requires_coupon and (not coupon or coupon.lower() != promo.requires_coupon.lower()):
            continue
        if promo.usage_limit and promo.times_used >= promo.usage_limit:
            continue
        for rule in promo.rules.all():
            if not _matches(rule.predicates or {}, cart=cart, channel=channel,
                            customer=customer, country=country, coupon=coupon):
                continue
            amount, free_ship, gift_pid = _apply_action(rule.action or {}, subtotal=subtotal)
            out.append(AppliedPromotion(
                promotion_id=str(promo.id),
                promotion_name=promo.name,
                rule_id=str(rule.id),
                discount_amount=amount,
                free_shipping=free_ship,
                gift_product_id=gift_pid,
                note=rule.label or '',
            ))
            break  # one rule per promo
    return out


def models_q_active(now):
    """Promotions where (starts_at is null or starts_at <= now) AND (ends_at is null or ends_at > now)."""
    from django.db.models import Q
    return (Q(starts_at__isnull=True) | Q(starts_at__lte=now)) & \
           (Q(ends_at__isnull=True) | Q(ends_at__gt=now))


def record_application(applied: AppliedPromotion, *, order_id: str = '', customer_id: str = '', currency: str = 'USD') -> None:
    from plugins.installed.promotions.models import PromotionApplication, Promotion
    try:
        PromotionApplication.objects.create(
            promotion_id=applied.promotion_id,
            rule_id=applied.rule_id,
            order_id=order_id,
            customer_id=customer_id,
            discount_amount=applied.discount_amount,
            currency=currency,
        )
        Promotion.objects.filter(id=applied.promotion_id).update(times_used=models_f_inc('times_used'))
    except Exception as e:  # noqa: BLE001
        logger.warning('promotions: record_application failed: %s', e)


def models_f_inc(field_name):
    from django.db.models import F
    return F(field_name) + 1
