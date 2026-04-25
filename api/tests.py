import json

from django.test import TestCase


class GraphQLAgentAuthTests(TestCase):
    def test_graphql_agent_requires_bearer_token(self):
        resp = self.client.post(
            '/graphql/agent/',
            data=json.dumps({'query': '{ ping }'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 401)

    def test_graphql_agent_accepts_valid_api_key(self):
        from core.models import APIKey, StoreChannel

        channel = StoreChannel.objects.create(name='Default', domain='example.test')
        api_key = APIKey.objects.create(
            name='Test Agent', scopes=['read:products'], channel=channel,
        )

        resp = self.client.post(
            '/graphql/agent/',
            data=json.dumps({'query': '{ ping }'}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {api_key.key}',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get('data', {}).get('ping'), 'pong')


class WebhookSignatureTests(TestCase):
    """The HMAC helper must produce stable, verifiable signatures."""

    def test_signature_round_trips(self):
        from core.tasks import compute_hmac_signature, verify_hmac_signature, _canonical_payload

        secret = 's3cret'
        payload = {'b': 2, 'a': 1, 'list': [1, 2, 3]}
        sig = compute_hmac_signature(secret, payload)
        self.assertTrue(verify_hmac_signature(secret, _canonical_payload(payload), sig))

    def test_signature_rejects_tampered_payload(self):
        from core.tasks import compute_hmac_signature, verify_hmac_signature, _canonical_payload

        secret = 's3cret'
        sig = compute_hmac_signature(secret, {'a': 1})
        self.assertFalse(verify_hmac_signature(secret, _canonical_payload({'a': 2}), sig))

    def test_signature_rejects_wrong_secret(self):
        from core.tasks import compute_hmac_signature, verify_hmac_signature, _canonical_payload

        sig = compute_hmac_signature('right', {'a': 1})
        self.assertFalse(verify_hmac_signature('wrong', _canonical_payload({'a': 1}), sig))


class GraphQLDepthLimitTests(TestCase):
    def test_depth_limit_rejects_deeply_nested_query(self):
        # Build a query that nests deeper than GRAPHQL_MAX_QUERY_DEPTH.
        depth = 30
        nested = '{ ping }'
        for _ in range(depth):
            nested = '{ a ' + nested + ' }'
        resp = self.client.post(
            '/graphql/',
            data=json.dumps({'query': nested}),
            content_type='application/json',
        )
        self.assertIn(resp.status_code, (400, 422))


class RestPermissionTests(TestCase):
    """REST defaults: products are public, orders require auth."""

    def test_products_are_public(self):
        resp = self.client.get('/v1/products/')
        self.assertIn(resp.status_code, (200, 301, 302))

    def test_orders_require_auth(self):
        resp = self.client.get('/v1/orders/')
        # DRF returns 401 with WWW-Authenticate, 403 otherwise.
        self.assertIn(resp.status_code, (401, 403))

    def test_legacy_rest_alias_removed(self):
        # The /rest/ duplicate of v1 should no longer exist.
        resp = self.client.get('/rest/products/')
        self.assertEqual(resp.status_code, 404)
