"""Order + cart services."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Dict, Optional

from django.db import transaction
from djmoney.money import Money

from core.hooks import MorpheusEvents, hook_registry
from plugins.installed.catalog.models import Product, ProductVariant
from plugins.installed.orders.models import Cart, CartItem, Order, OrderItem

logger = logging.getLogger('morpheus.orders')


class CartService:

    @classmethod
    def get_or_create_cart(cls, session_key: str = '', customer=None) -> Cart:
        if customer:
            cart, _ = Cart.objects.get_or_create(customer=customer)
        else:
            cart, _ = Cart.objects.get_or_create(session_key=session_key, customer=None)
        return cart

    @classmethod
    def add_item(
        cls, cart: Cart, product_id: str, quantity: int = 1, variant_id: Optional[str] = None,
    ) -> CartItem:
        product = Product.objects.get(id=product_id)
        variant = ProductVariant.objects.get(id=variant_id) if variant_id else None
        unit_price = variant.effective_price if variant else product.price

        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, variant=variant,
            defaults={'quantity': quantity, 'unit_price': unit_price},
        )
        if not created:
            item.quantity += quantity
            item.save(update_fields=['quantity'])
        return item


class OrderService:

    @classmethod
    @transaction.atomic
    def create_from_cart(
        cls, cart: Cart, email: str,
        shipping_address: Dict, billing_address: Dict,
    ) -> Order:
        if not cart.items.exists():
            raise ValueError('Cannot place an order from an empty cart.')

        items = list(cart.items.select_related('product', 'variant').all())
        currency = str(items[0].unit_price.currency)
        subtotal = Money(
            sum((Decimal(it.unit_price.amount) * it.quantity for it in items), Decimal('0')),
            currency,
        )

        order = Order.objects.create(
            customer=cart.customer,
            email=email,
            shipping_address=shipping_address,
            billing_address=billing_address,
            subtotal=subtotal,
            total=subtotal,  # tax + shipping engines plug in here later
        )

        for cart_item in items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                variant=cart_item.variant,
                product_name=cart_item.product.name,
                variant_name=cart_item.variant.name if cart_item.variant else '',
                sku=cart_item.variant.sku if cart_item.variant else cart_item.product.sku,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                total_price=cart_item.total_price,
            )

        cart.items.all().delete()

        hook_registry.fire(MorpheusEvents.ORDER_PLACED, order=order)
        return order

    @classmethod
    def confirm_order(cls, order: Order) -> None:
        order.confirm()  # FSM transition; raises if not in `pending`
        order.save()
        hook_registry.fire(MorpheusEvents.ORDER_CONFIRMED, order=order)
