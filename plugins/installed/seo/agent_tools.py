"""SEO tools the agent layer can call."""
from __future__ import annotations

from core.agents import ToolError, ToolResult, tool


@tool(
    name='seo.get_meta',
    description='Read SEO meta (title/description/keywords) for a product by slug.',
    scopes=['seo.read'],
    schema={
        'type': 'object',
        'properties': {'slug': {'type': 'string'}},
        'required': ['slug'],
    },
)
def get_meta_tool(*, slug: str) -> ToolResult:
    from django.contrib.contenttypes.models import ContentType
    from plugins.installed.catalog.models import Product
    from plugins.installed.seo.models import SeoMeta

    try:
        product = Product.objects.get(slug=slug)
    except Product.DoesNotExist as e:
        raise ToolError(f'Unknown product: {slug}') from e
    ct = ContentType.objects.get_for_model(Product)
    try:
        meta = SeoMeta.objects.get(content_type=ct, object_id=str(product.id))
    except SeoMeta.DoesNotExist:
        return ToolResult(output={'slug': slug, 'meta': None})
    return ToolResult(output={
        'slug': slug,
        'meta': {
            'title': meta.title,
            'description': meta.description,
            'keywords': meta.keywords,
        },
    })


@tool(
    name='seo.set_meta',
    description='Set SEO meta (title/description/keywords) for a product by slug. Empty string clears a field.',
    scopes=['seo.write'],
    schema={
        'type': 'object',
        'properties': {
            'slug': {'type': 'string'},
            'title': {'type': 'string'},
            'description': {'type': 'string'},
            'keywords': {'type': 'string'},
        },
        'required': ['slug'],
    },
    requires_approval=True,
)
def set_meta_tool(
    *, slug: str, title: str = '', description: str = '', keywords: str = '',
) -> ToolResult:
    from django.contrib.contenttypes.models import ContentType
    from plugins.installed.catalog.models import Product
    from plugins.installed.seo.models import SeoMeta

    try:
        product = Product.objects.get(slug=slug)
    except Product.DoesNotExist as e:
        raise ToolError(f'Unknown product: {slug}') from e
    ct = ContentType.objects.get_for_model(Product)
    meta, _ = SeoMeta.objects.update_or_create(
        content_type=ct, object_id=str(product.id),
        defaults={
            'title': title[:200],
            'description': description[:500],
            'keywords': keywords[:300],
        },
    )
    return ToolResult(
        output={'slug': slug, 'title': meta.title, 'description': meta.description},
        display=f'Updated SEO meta for {slug}',
    )
