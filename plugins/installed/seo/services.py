"""
SEO service layer: meta resolution, JSON-LD generation, sitemap building,
and AI-driven autofill.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Iterable
from urllib.parse import urljoin

from django.conf import settings
from django.utils.html import escape

logger = logging.getLogger('morpheus.seo')


@dataclass(slots=True)
class ResolvedMeta:
    """Concrete, fallback-resolved meta values ready for rendering."""
    title: str = ''
    description: str = ''
    og_title: str = ''
    og_description: str = ''
    og_image: str = ''
    og_type: str = 'website'
    twitter_card: str = 'summary_large_image'
    canonical_url: str = ''
    robots: str = 'index, follow'
    keywords: str = ''
    structured_data: dict = None  # type: ignore[assignment]

    def to_html(self) -> str:
        """Render the meta tags as an HTML fragment for the <head>."""
        parts: list[str] = []
        if self.title:
            parts.append(f'<title>{escape(self.title)}</title>')
        if self.description:
            parts.append(f'<meta name="description" content="{escape(self.description)}">')
        if self.keywords:
            parts.append(f'<meta name="keywords" content="{escape(self.keywords)}">')
        if self.robots:
            parts.append(f'<meta name="robots" content="{escape(self.robots)}">')
        if self.canonical_url:
            parts.append(f'<link rel="canonical" href="{escape(self.canonical_url)}">')

        og_title = self.og_title or self.title
        og_desc = self.og_description or self.description
        if og_title:
            parts.append(f'<meta property="og:title" content="{escape(og_title)}">')
        if og_desc:
            parts.append(f'<meta property="og:description" content="{escape(og_desc)}">')
        parts.append(f'<meta property="og:type" content="{escape(self.og_type)}">')
        if self.og_image:
            parts.append(f'<meta property="og:image" content="{escape(self.og_image)}">')

        parts.append(f'<meta name="twitter:card" content="{escape(self.twitter_card)}">')
        if og_title:
            parts.append(f'<meta name="twitter:title" content="{escape(og_title)}">')
        if og_desc:
            parts.append(f'<meta name="twitter:description" content="{escape(og_desc)}">')
        if self.og_image:
            parts.append(f'<meta name="twitter:image" content="{escape(self.og_image)}">')

        if self.structured_data:
            parts.append(
                '<script type="application/ld+json">'
                + json.dumps(self.structured_data, separators=(',', ':'))
                + '</script>'
            )
        return '\n'.join(parts)


def resolve_meta(
    *,
    obj: Any | None = None,
    fallback_title: str = '',
    fallback_description: str = '',
    fallback_image: str = '',
    canonical_url: str = '',
    og_type: str = 'website',
) -> ResolvedMeta:
    """Merge per-object SeoMeta with fallback values into a ResolvedMeta."""
    from plugins.installed.seo.models import SeoMeta

    meta = SeoMeta.for_obj(obj) if obj is not None else None

    title = (meta.title if meta and meta.title else fallback_title).strip()
    description = (meta.description if meta and meta.description else fallback_description).strip()
    og_image = (meta.og_image if meta and meta.og_image else fallback_image).strip()
    canonical = (meta.canonical_url if meta and meta.canonical_url else canonical_url).strip()
    robots = meta.robots if meta else 'index, follow'
    keywords = meta.keywords if meta else ''
    twitter_card = meta.twitter_card if meta else 'summary_large_image'
    type_ = (meta.og_type if meta and meta.og_type else og_type)

    structured = _structured_data_for(obj, title=title, description=description, image=og_image)
    if meta and meta.structured_data:
        structured = {**structured, **meta.structured_data}

    return ResolvedMeta(
        title=title,
        description=description,
        og_title=meta.og_title if meta else '',
        og_description=meta.og_description if meta else '',
        og_image=og_image,
        og_type=type_,
        twitter_card=twitter_card,
        canonical_url=canonical,
        robots=robots,
        keywords=keywords,
        structured_data=structured,
    )


def _structured_data_for(obj: Any, *, title: str, description: str, image: str) -> dict:
    """Generate sensible JSON-LD for known model types. Empty dict if unknown."""
    if obj is None:
        return {
            '@context': 'https://schema.org',
            '@type': 'Organization',
            'name': getattr(settings, 'STORE_NAME', 'Morpheus Store'),
        }
    cls_name = type(obj).__name__
    if cls_name == 'Product':
        try:
            price_amount = str(obj.price.amount) if obj.price else ''
            price_currency = str(obj.price.currency) if obj.price else 'USD'
        except Exception:  # noqa: BLE001 — degrade gracefully on price-field oddities
            price_amount = ''
            price_currency = 'USD'
        return {
            '@context': 'https://schema.org',
            '@type': 'Product',
            'name': title or getattr(obj, 'name', ''),
            'description': description or getattr(obj, 'short_description', ''),
            'image': [image] if image else [],
            'sku': getattr(obj, 'sku', ''),
            'offers': {
                '@type': 'Offer',
                'price': price_amount,
                'priceCurrency': price_currency,
                'availability': 'https://schema.org/InStock',
            },
        }
    if cls_name in ('Category', 'Collection'):
        return {
            '@context': 'https://schema.org',
            '@type': 'CollectionPage',
            'name': title or getattr(obj, 'name', ''),
            'description': description or getattr(obj, 'description', ''),
        }
    return {}


# ── Sitemap ────────────────────────────────────────────────────────────────────


def iter_sitemap_entries() -> Iterable[dict]:
    """
    Yield entries that should appear in the sitemap. Pulls from:
      1. Active products (catalog)
      2. Active categories (catalog)
      3. Active collections (catalog)
      4. Manually-curated SitemapEntry rows
    """
    base = _site_base_url()

    yield {'loc': base, 'changefreq': 'daily', 'priority': '1.0'}

    try:
        from plugins.installed.catalog.models import Category, Collection, Product
        for p in Product.objects.filter(status='active').only('slug', 'updated_at'):
            yield {
                'loc': urljoin(base, f'/products/{p.slug}/'),
                'lastmod': p.updated_at.isoformat() if p.updated_at else '',
                'changefreq': 'weekly',
                'priority': '0.8',
            }
        for c in Category.objects.filter(is_active=True).only('slug', 'updated_at'):
            yield {
                'loc': urljoin(base, f'/products/?category={c.slug}'),
                'lastmod': c.updated_at.isoformat() if c.updated_at else '',
                'changefreq': 'weekly',
                'priority': '0.6',
            }
        for col in Collection.objects.filter(is_active=True).only('slug', 'updated_at'):
            yield {
                'loc': urljoin(base, f'/c/{col.slug}/'),
                'lastmod': col.updated_at.isoformat() if col.updated_at else '',
                'changefreq': 'weekly',
                'priority': '0.6',
            }
    except Exception as e:  # noqa: BLE001 — catalog plugin is optional
        logger.debug('seo: sitemap catalog skipped: %s', e)

    try:
        from plugins.installed.seo.models import SitemapEntry
        for row in SitemapEntry.objects.filter(is_active=True):
            yield {
                'loc': row.location,
                'lastmod': row.last_modified.isoformat() if row.last_modified else '',
                'changefreq': row.changefreq,
                'priority': str(row.priority),
            }
    except Exception as e:  # noqa: BLE001
        logger.debug('seo: manual sitemap entries skipped: %s', e)


def render_sitemap_xml() -> str:
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for e in iter_sitemap_entries():
        parts.append('<url>')
        parts.append(f'<loc>{escape(e["loc"])}</loc>')
        if e.get('lastmod'):
            parts.append(f'<lastmod>{escape(e["lastmod"])}</lastmod>')
        if e.get('changefreq'):
            parts.append(f'<changefreq>{escape(e["changefreq"])}</changefreq>')
        if e.get('priority'):
            parts.append(f'<priority>{escape(e["priority"])}</priority>')
        parts.append('</url>')
    parts.append('</urlset>')
    return ''.join(parts)


def render_robots_txt() -> str:
    base = _site_base_url()
    lines = [
        'User-agent: *',
        'Allow: /',
        'Disallow: /admin/',
        'Disallow: /dashboard/',
        'Disallow: /accounts/',
        'Disallow: /cart/',
        'Disallow: /checkout/',
        f'Sitemap: {urljoin(base, "/sitemap.xml")}',
    ]
    return '\n'.join(lines) + '\n'


def _site_base_url() -> str:
    base = getattr(settings, 'SITE_BASE_URL', '').rstrip('/')
    if base:
        return base + '/'
    hosts = getattr(settings, 'ALLOWED_HOSTS', []) or ['localhost']
    return f'https://{hosts[0]}/'


# ── Redirect resolution ────────────────────────────────────────────────────────


def resolve_redirect(path: str) -> tuple[str, int] | None:
    """Return (target_path, status_code) for `path`, or None if no alias exists."""
    from django.db import DatabaseError
    from django.utils import timezone

    from plugins.installed.seo.models import Redirect

    try:
        row = Redirect.objects.filter(from_path=path, is_active=True).first()
    except DatabaseError as e:
        logger.warning('seo: redirect lookup db error: %s', e)
        return None
    if row is None:
        return None
    try:
        Redirect.objects.filter(pk=row.pk).update(
            hit_count=row.hit_count + 1,
            last_hit_at=timezone.now(),
        )
    except DatabaseError:
        pass
    return row.to_path, row.status_code


# ── Autofill via ai_content (optional) ─────────────────────────────────────────


def autofill_meta_for(obj: Any) -> 'SeoMeta | None':  # noqa: F821
    """If the merchant left meta fields blank, fill them with sensible defaults
    derived from the host model. The AI plugin can override this later."""
    from django.contrib.contenttypes.models import ContentType

    from plugins.installed.seo.models import SeoMeta

    ct = ContentType.objects.get_for_model(type(obj))
    meta, _ = SeoMeta.objects.get_or_create(content_type=ct, object_id=str(obj.pk))

    if not meta.title:
        meta.title = (
            f'{getattr(obj, "name", "")} — {getattr(settings, "STORE_NAME", "Morpheus Store")}'
        ).strip(' —')
    if not meta.description:
        desc = getattr(obj, 'short_description', '') or getattr(obj, 'description', '')
        meta.description = (desc or '')[:300]
    if not meta.og_image:
        primary = getattr(obj, 'primary_image', None)
        if primary and getattr(primary, 'image', None):
            try:
                meta.og_image = primary.image.url
            except Exception:  # noqa: BLE001 — image may not have a URL on disk
                pass
    if not meta.auto_filled:
        meta.auto_filled = True
    meta.save()
    return meta
