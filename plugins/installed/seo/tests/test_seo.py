"""SEO plugin tests: meta resolution, sitemap, redirect, autofill."""
from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase
from djmoney.money import Money

from plugins.installed.catalog.models import Product
from plugins.installed.seo.middleware import SeoRedirectMiddleware
from plugins.installed.seo.models import Redirect, SeoMeta
from plugins.installed.seo.services import (
    autofill_meta_for,
    render_robots_txt,
    render_sitemap_xml,
    resolve_meta,
    resolve_redirect,
)


class ResolveMetaTests(TestCase):

    def test_returns_fallbacks_when_no_meta(self):
        out = resolve_meta(
            obj=None,
            fallback_title='dot books.',
            fallback_description='A quieter shelf.',
        )
        self.assertEqual(out.title, 'dot books.')
        self.assertEqual(out.description, 'A quieter shelf.')

    def test_overrides_with_seo_meta_row(self):
        product = Product.objects.create(
            name='Test', slug='test', sku='T1',
            price=Money(10, 'USD'), status='active',
        )
        ct = ContentType.objects.get_for_model(Product)
        # Hook autofills the SeoMeta on product create — overwrite it here.
        SeoMeta.objects.update_or_create(
            content_type=ct, object_id=str(product.pk),
            defaults={
                'title': 'Custom Title',
                'description': 'Custom Description',
                'og_image': 'https://example.com/cover.jpg',
            },
        )
        out = resolve_meta(obj=product, fallback_title='ignored', fallback_description='ignored')
        self.assertEqual(out.title, 'Custom Title')
        self.assertEqual(out.description, 'Custom Description')
        self.assertEqual(out.og_image, 'https://example.com/cover.jpg')
        # JSON-LD includes Product schema
        self.assertEqual(out.structured_data.get('@type'), 'Product')

    def test_to_html_emits_required_tags(self):
        out = resolve_meta(
            obj=None,
            fallback_title='Hello',
            fallback_description='World',
            fallback_image='https://example.com/img.png',
        )
        html = out.to_html()
        self.assertIn('<title>Hello</title>', html)
        self.assertIn('<meta name="description" content="World">', html)
        self.assertIn('og:image', html)
        self.assertIn('twitter:card', html)
        self.assertIn('application/ld+json', html)


class AutofillTests(TestCase):

    def test_autofill_for_product(self):
        product = Product.objects.create(
            name='Sample Book', slug='sample-book', sku='S1',
            short_description='A wonderful read.',
            price=Money(20, 'USD'), status='active',
        )
        meta = autofill_meta_for(product)
        self.assertIsNotNone(meta)
        self.assertIn('Sample Book', meta.title)
        self.assertEqual(meta.description, 'A wonderful read.')
        self.assertTrue(meta.auto_filled)


class RedirectTests(TestCase):

    def test_resolve_redirect_returns_target(self):
        Redirect.objects.create(
            from_path='/old/', to_path='/new/', status_code=301, is_active=True,
        )
        target = resolve_redirect('/old/')
        self.assertEqual(target, ('/new/', 301))

    def test_resolve_unknown_path_returns_none(self):
        self.assertIsNone(resolve_redirect('/no-match/'))

    def test_redirect_increments_hit_count(self):
        r = Redirect.objects.create(
            from_path='/a/', to_path='/b/', is_active=True,
        )
        resolve_redirect('/a/')
        r.refresh_from_db()
        self.assertEqual(r.hit_count, 1)
        self.assertIsNotNone(r.last_hit_at)


class MiddlewareTests(TestCase):

    def setUp(self) -> None:
        Redirect.objects.create(
            from_path='/legacy/', to_path='/new-home/', status_code=301, is_active=True,
        )
        self.rf = RequestFactory()

    def test_middleware_redirects_known_path(self):
        mw = SeoRedirectMiddleware(get_response=lambda r: None)
        resp = mw(self.rf.get('/legacy/'))
        self.assertEqual(resp.status_code, 301)
        self.assertEqual(resp['Location'], '/new-home/')

    def test_middleware_passes_through_skipped_prefixes(self):
        called = {'hit': False}

        def view(request):
            called['hit'] = True
            return 'ok'

        mw = SeoRedirectMiddleware(get_response=view)
        mw(self.rf.get('/admin/foo'))
        self.assertTrue(called['hit'])


class SitemapTests(TestCase):

    def test_sitemap_renders_when_empty_catalog(self):
        xml = render_sitemap_xml()
        self.assertIn('<?xml', xml)
        self.assertIn('<urlset', xml)

    def test_sitemap_includes_active_products(self):
        Product.objects.create(
            name='SEO Test', slug='seo-test', sku='SEO1',
            price=Money(10, 'USD'), status='active',
        )
        xml = render_sitemap_xml()
        self.assertIn('seo-test', xml)

    def test_robots_lists_sitemap(self):
        txt = render_robots_txt()
        self.assertIn('User-agent: *', txt)
        self.assertIn('Sitemap:', txt)
        self.assertIn('Disallow: /admin/', txt)


# ─────────────────────────────────────────────────────────────────────────────
# Deep-SEO tests
# ─────────────────────────────────────────────────────────────────────────────

import sys as _sys
_IS_SQLITE = 'sqlite' in (_sys.modules.get('django.conf').settings.DATABASES['default']['ENGINE']
                           if 'django.conf' in _sys.modules else '')


class DeepSeoServicesTests(TestCase):

    def test_render_llms_txt(self):
        from plugins.installed.seo.services import render_llms_txt
        out = render_llms_txt(full=False)
        self.assertIn('# ', out)
        self.assertIn('## Site map', out)

    def test_organization_jsonld_returns_none_when_no_org_name(self):
        from plugins.installed.seo.services import organization_jsonld
        # Nothing configured → returns None.
        self.assertIsNone(organization_jsonld())

    def test_organization_jsonld_with_settings(self):
        from plugins.installed.seo.models import SiteSeoSettings
        from plugins.installed.seo.services import organization_jsonld

        SiteSeoSettings.objects.create(
            organization_name='Acme Books',
            organization_logo_url='https://example.com/logo.png',
            facebook_url='https://facebook.com/acme',
        )
        obj = organization_jsonld()
        self.assertIsNotNone(obj)
        self.assertEqual(obj['@type'], 'Organization')
        self.assertEqual(obj['name'], 'Acme Books')
        self.assertIn('https://facebook.com/acme', obj['sameAs'])

    def test_404_log_records_and_dedupes(self):
        from plugins.installed.seo.models import NotFoundLog
        from plugins.installed.seo.services import record_404
        record_404(path='/missing/', referrer='https://example.com/')
        record_404(path='/missing/')
        record_404(path='/missing/')
        log = NotFoundLog.objects.get(path='/missing/')
        self.assertEqual(log.hit_count, 3)

    def test_audit_product_low_score_when_empty(self):
        from decimal import Decimal
        from djmoney.money import Money
        from plugins.installed.catalog.models import Product
        from plugins.installed.seo.services import audit_product

        p = Product.objects.create(
            name='X', slug='product-bad', sku='X1',
            price=Money(Decimal('10'), 'USD'), status='active',
        )
        result = audit_product(p)
        # Has weak slug + no description → score reduced
        self.assertLess(result['score'], 100)
        self.assertTrue(any(i['code'] == 'weak_slug' for i in result['issues']))


class DeepSeoAgentToolsTests(TestCase):

    def test_tools_registered(self):
        from core.agents import agent_registry
        names = {t.name for t in agent_registry.platform_tools()}
        for required in ('seo.audit_product', 'seo.audit_all', 'seo.list_404s',
                         'seo.create_redirect', 'seo.bulk_set_meta',
                         'seo.set_site_settings'):
            self.assertIn(required, names)
