"""Catalog tools — read-only product/category access for agents."""
from __future__ import annotations

from core.agents import ToolError, ToolResult, tool


@tool(
    name='catalog.find_products',
    description='Search active products by free-text query. Returns up to `limit` matches with name, slug, price and short description.',
    scopes=['catalog.read'],
    schema={
        'type': 'object',
        'properties': {
            'query': {'type': 'string', 'description': 'Search terms.'},
            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 25, 'default': 8},
        },
        'required': ['query'],
    },
)
def find_products_tool(*, query: str, limit: int = 8) -> ToolResult:
    from django.db.models import Q
    from plugins.installed.catalog.models import Product

    q = (query or '').strip()
    if not q:
        return ToolResult(output={'products': []})
    limit = max(1, min(int(limit or 8), 25))
    qs = (
        Product.objects.filter(status='active')
        .filter(Q(name__icontains=q) | Q(short_description__icontains=q) | Q(sku__iexact=q))
        .order_by('-created_at')[:limit]
    )
    products = [
        {
            'id': str(p.id),
            'slug': p.slug,
            'name': p.name,
            'sku': p.sku,
            'price': str(getattr(p.price, 'amount', '')),
            'currency': str(getattr(p.price, 'currency', '')),
            'short_description': p.short_description or '',
            'url': f'/products/{p.slug}/',
        }
        for p in qs
    ]
    return ToolResult(output={'products': products}, display=f'{len(products)} match(es) for {q!r}')


@tool(
    name='catalog.get_product',
    description='Look up a single product by slug or SKU.',
    scopes=['catalog.read'],
    schema={
        'type': 'object',
        'properties': {
            'slug': {'type': 'string'},
            'sku': {'type': 'string'},
        },
    },
)
def get_product_tool(*, slug: str = '', sku: str = '') -> ToolResult:
    from plugins.installed.catalog.models import Product

    if not slug and not sku:
        raise ToolError('Provide either slug or sku.')
    qs = Product.objects.filter(status='active')
    if slug:
        qs = qs.filter(slug=slug)
    if sku:
        qs = qs.filter(sku__iexact=sku)
    p = qs.first()
    if not p:
        return ToolResult(output={'product': None}, display='Not found')
    return ToolResult(output={'product': {
        'id': str(p.id),
        'slug': p.slug,
        'name': p.name,
        'sku': p.sku,
        'description': p.description or '',
        'short_description': p.short_description or '',
        'price': str(getattr(p.price, 'amount', '')),
        'currency': str(getattr(p.price, 'currency', '')),
        'category': p.category.name if p.category_id else '',
        'is_on_sale': bool(getattr(p, 'is_on_sale', False)),
    }})


@tool(
    name='catalog.list_categories',
    description='List top-level product categories.',
    scopes=['catalog.read'],
    schema={'type': 'object', 'properties': {}},
)
def list_categories_tool() -> ToolResult:
    from plugins.installed.catalog.models import Category

    cats = Category.objects.filter(parent__isnull=True).order_by('name')[:50]
    return ToolResult(output={
        'categories': [{'slug': c.slug, 'name': c.name} for c in cats],
    })
