"""
Template tags for the SEO plugin.

Usage:

    {% load seo %}
    <head>
      ...
      {% seo_meta object=product fallback_title="dot books." fallback_description="A quieter shelf for louder books." %}
    </head>

The tag emits <title>, meta description, OG, Twitter Card, canonical link,
robots, keywords, and a JSON-LD <script>.
"""
from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

from plugins.installed.seo.services import resolve_meta

register = template.Library()


@register.simple_tag(takes_context=True)
def seo_meta(
    context,
    object=None,
    fallback_title: str = '',
    fallback_description: str = '',
    fallback_image: str = '',
    canonical_url: str = '',
    og_type: str = 'website',
):
    request = context.get('request')
    if not canonical_url and request is not None:
        try:
            canonical_url = request.build_absolute_uri()
        except Exception:  # noqa: BLE001 — request may not have a host configured
            canonical_url = ''

    meta = resolve_meta(
        obj=object,
        fallback_title=fallback_title,
        fallback_description=fallback_description,
        fallback_image=fallback_image,
        canonical_url=canonical_url,
        og_type=og_type,
    )
    return mark_safe(meta.to_html())


@register.simple_tag
def seo_organization_jsonld():
    """Emit <script type="application/ld+json"> for the Organization."""
    from plugins.installed.seo.services import organization_jsonld, _jsonld_dump
    obj = organization_jsonld()
    if not obj:
        return ''
    return mark_safe(f'<script type="application/ld+json">{_jsonld_dump(obj)}</script>')


@register.simple_tag
def seo_website_jsonld():
    """Emit <script type="application/ld+json"> for the WebSite (sitelinks search)."""
    from plugins.installed.seo.services import website_jsonld, _jsonld_dump
    obj = website_jsonld()
    if not obj:
        return ''
    return mark_safe(f'<script type="application/ld+json">{_jsonld_dump(obj)}</script>')


@register.simple_tag
def seo_product_jsonld(product):
    """Emit Product JSON-LD with offer / availability / aggregateRating."""
    if product is None:
        return ''
    from plugins.installed.seo.services import product_jsonld, _jsonld_dump
    return mark_safe(f'<script type="application/ld+json">{_jsonld_dump(product_jsonld(product))}</script>')


@register.simple_tag
def seo_breadcrumb_jsonld(items):
    """Emit BreadcrumbList JSON-LD. `items` is a list of {name, url}."""
    if not items:
        return ''
    from plugins.installed.seo.services import breadcrumb_jsonld, _jsonld_dump
    return mark_safe(f'<script type="application/ld+json">{_jsonld_dump(breadcrumb_jsonld(items))}</script>')


@register.simple_tag
def seo_verification_metas():
    """Emit any configured Google / Bing / Pinterest / FB verification metas."""
    from plugins.installed.seo.services import site_settings
    s = site_settings()
    out = []
    pairs = [
        ('google-site-verification', s.google_site_verification),
        ('msvalidate.01', s.bing_verification),
        ('p:domain_verify', s.pinterest_verification),
        ('facebook-domain-verification', s.facebook_domain_verification),
    ]
    for name, content in pairs:
        if content:
            out.append(f'<meta name="{name}" content="{content}">')
    return mark_safe('\n'.join(out))


@register.simple_tag
def seo_llms_link():
    """Emit a <link rel="alternate"> hint to /llms.txt for LLM crawlers."""
    from plugins.installed.seo.services import site_settings
    s = site_settings()
    if not s.llms_txt_enabled:
        return ''
    return mark_safe('<link rel="alternate" type="text/plain" href="/llms.txt" title="LLM-friendly site map">')
