"""Idempotent loader for the demo bookstore dataset."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from djmoney.money import Money

from plugins.installed.demo_data import seeds

logger = logging.getLogger('morpheus.demo_data')


@dataclass
class SeedSummary:
    counts: dict[str, int] = field(default_factory=dict)

    def inc(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n


def seed_all(*, currency: str = 'USD', wipe: bool = False) -> SeedSummary:
    """Seed the demo dataset. Re-runnable; will not duplicate rows.

    Args:
        currency: ISO currency code for prices.
        wipe: if True, deletes existing demo rows first (DESTRUCTIVE).
    """
    summary = SeedSummary()

    if wipe:
        _wipe_demo(summary)

    with transaction.atomic():
        cat_by_slug = _seed_categories(summary)
        col_by_slug = _seed_collections(summary)
        ven_by_slug = _seed_vendors(summary)
        _seed_books(summary, cat_by_slug, ven_by_slug, col_by_slug, currency)
        _seed_customers(summary)
        _seed_orders(summary, currency)

    return summary


def _seed_categories(summary: SeedSummary) -> dict[str, Any]:
    from plugins.installed.catalog.models import Category

    by_slug: dict[str, Any] = {}
    for entry in seeds.CATEGORIES:
        cat, created = Category.objects.update_or_create(
            slug=entry['slug'],
            defaults={'name': entry['name'], 'is_active': True},
        )
        by_slug[entry['slug']] = cat
        if created:
            summary.inc('categories')
    return by_slug


def _seed_collections(summary: SeedSummary) -> dict[str, Any]:
    from plugins.installed.catalog.models import Collection

    by_slug: dict[str, Any] = {}
    for entry in seeds.COLLECTIONS:
        col, created = Collection.objects.update_or_create(
            slug=entry['slug'],
            defaults={
                'name': entry['name'],
                'description': entry['description'],
                'is_active': True,
                'is_featured': entry.get('is_featured', False),
            },
        )
        by_slug[entry['slug']] = col
        if created:
            summary.inc('collections')
    return by_slug


def _seed_vendors(summary: SeedSummary) -> dict[str, Any]:
    from plugins.installed.catalog.models import Vendor

    by_slug: dict[str, Any] = {}
    for entry in seeds.VENDORS:
        v, created = Vendor.objects.update_or_create(
            slug=entry['slug'],
            defaults={
                'name': entry['name'],
                'commission_rate': Decimal(entry['commission_rate']),
                'is_active': True,
            },
        )
        by_slug[entry['slug']] = v
        if created:
            summary.inc('vendors')
    return by_slug


def _seed_books(
    summary: SeedSummary,
    cat_by_slug: dict[str, Any],
    ven_by_slug: dict[str, Any],
    col_by_slug: dict[str, Any],
    currency: str,
) -> None:
    from plugins.installed.catalog.models import Product

    featured_collection = col_by_slug.get('reading-the-spring')
    pick_collection = col_by_slug.get('editors-pick-april')

    for row in seeds.BOOKS:
        (name, slug, sku, cat_slug, ven_slug, price, short_desc, desc, featured) = row
        defaults = {
            'name': name,
            'sku': sku,
            'short_description': short_desc,
            'description': desc,
            'price': Money(Decimal(price), currency),
            'status': 'active',
            'is_featured': featured,
            'category': cat_by_slug.get(cat_slug),
            'vendor': ven_by_slug.get(ven_slug),
        }
        product, created = Product.objects.update_or_create(slug=slug, defaults=defaults)
        if created:
            summary.inc('books')
        # Attach to a collection or two
        if featured and pick_collection is not None:
            product.collections.add(pick_collection)
        if featured_collection is not None:
            product.collections.add(featured_collection)


def _seed_customers(summary: SeedSummary) -> None:
    User = get_user_model()
    demo_customers = [
        {'email': 'reader.one@example.com',  'first_name': 'Mara',  'last_name': 'Holst'},
        {'email': 'reader.two@example.com',  'first_name': 'Idris', 'last_name': 'Khan'},
        {'email': 'reader.three@example.com', 'first_name': 'Lucia', 'last_name': 'Berg'},
    ]
    for c in demo_customers:
        user, created = User.objects.get_or_create(
            email=c['email'],
            defaults={'first_name': c['first_name'], 'last_name': c['last_name']},
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=['password'])
            summary.inc('customers')


def _seed_orders(summary: SeedSummary, currency: str) -> None:
    """Create a couple of completed orders for nicer dashboard numbers."""
    from django.contrib.auth import get_user_model
    from plugins.installed.catalog.models import Product
    from plugins.installed.orders.models import Order, OrderItem

    User = get_user_model()
    customer = User.objects.filter(email='reader.one@example.com').first()
    if customer is None:
        return
    book_a = Product.objects.filter(slug='on-quiet-hours').first()
    book_b = Product.objects.filter(slug='unfinished-light').first()
    if not book_a or not book_b:
        return

    if Order.objects.filter(email=customer.email).exists():
        return  # already seeded

    subtotal = Money(Decimal('32.00'), currency)
    order = Order.objects.create(
        customer=customer,
        email=customer.email,
        subtotal=subtotal,
        total=subtotal,
        payment_status='paid',
        source='demo',
    )
    OrderItem.objects.create(
        order=order, product=book_a, product_name=book_a.name,
        quantity=1, unit_price=book_a.price, total_price=book_a.price,
    )
    OrderItem.objects.create(
        order=order, product=book_b, product_name=book_b.name,
        quantity=1, unit_price=book_b.price, total_price=book_b.price,
    )
    summary.inc('orders')


# ── Wipe (DESTRUCTIVE — hidden behind --fresh) ─────────────────────────────────


def _wipe_demo(summary: SeedSummary) -> None:
    """Remove rows seeded by this loader. Identifies them by slug/email."""
    from plugins.installed.catalog.models import Category, Collection, Product, Vendor
    from plugins.installed.orders.models import Order

    book_slugs = [b[1] for b in seeds.BOOKS]
    Product.objects.filter(slug__in=book_slugs).delete()
    Collection.objects.filter(slug__in=[c['slug'] for c in seeds.COLLECTIONS]).delete()
    Category.objects.filter(slug__in=[c['slug'] for c in seeds.CATEGORIES]).delete()
    Vendor.objects.filter(slug__in=[v['slug'] for v in seeds.VENDORS]).delete()
    Order.objects.filter(source='demo').delete()
    summary.inc('wiped', 1)
