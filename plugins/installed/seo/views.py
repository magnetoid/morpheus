"""SEO views — sitemap.xml + robots.txt."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse

from plugins.installed.seo.services import render_robots_txt, render_sitemap_xml


def sitemap_xml(request: HttpRequest) -> HttpResponse:
    return HttpResponse(render_sitemap_xml(), content_type='application/xml; charset=utf-8')


def robots_txt(request: HttpRequest) -> HttpResponse:
    return HttpResponse(render_robots_txt(), content_type='text/plain; charset=utf-8')
