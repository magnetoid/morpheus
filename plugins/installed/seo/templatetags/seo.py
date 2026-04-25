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
