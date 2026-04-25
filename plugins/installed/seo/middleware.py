"""SEO redirect middleware: applies /old/ -> /new/ aliases before the view runs."""
from __future__ import annotations

from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect


class SeoRedirectMiddleware:
    """Resolve `request.path_info` against the Redirect table and 301 if matched.

    Skipped for hot paths so we don't pay the DB lookup on every request:
    static/media files, the admin, the dashboard, and the GraphQL endpoints.
    """

    SKIP_PREFIXES = (
        '/static/', '/media/', '/admin/', '/dashboard/',
        '/graphql', '/v1/', '/healthz', '/readyz',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info or '/'
        for prefix in self.SKIP_PREFIXES:
            if path.startswith(prefix):
                return self.get_response(request)
        from plugins.installed.seo.services import resolve_redirect
        target = resolve_redirect(path)
        if target is None:
            return self.get_response(request)
        to_path, status = target
        if status == 301:
            return HttpResponsePermanentRedirect(to_path)
        return HttpResponseRedirect(to_path)
