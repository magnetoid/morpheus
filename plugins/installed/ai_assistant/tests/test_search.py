"""Tests for the embedding-aware semantic search service."""
from __future__ import annotations

from django.test import TestCase
from djmoney.money import Money

from plugins.installed.ai_assistant.models import ProductEmbedding
from plugins.installed.ai_assistant.services.embeddings import (
    EMBEDDING_DIM,
    cosine_similarity,
    embed,
)
from plugins.installed.ai_assistant.services.search import (
    semantic_search,
    upsert_product_embedding,
)
from plugins.installed.catalog.models import Product


class EmbeddingTests(TestCase):

    def test_embed_returns_fixed_dim_floats(self):
        v = embed('hello world')
        self.assertEqual(len(v), EMBEDDING_DIM)
        self.assertTrue(all(isinstance(x, float) for x in v))

    def test_embed_is_deterministic(self):
        self.assertEqual(embed('blender'), embed('blender'))

    def test_cosine_self_similarity_is_one(self):
        v = embed('cup')
        self.assertAlmostEqual(cosine_similarity(v, v), 1.0, places=4)


class SemanticSearchTests(TestCase):

    def setUp(self) -> None:
        self.p1 = Product.objects.create(
            name='Pro Blender', slug='pro-blender', sku='B1',
            short_description='powerful kitchen blender',
            description='professional grade blender for smoothies',
            price=Money(75, 'USD'), status='active',
        )
        self.p2 = Product.objects.create(
            name='Toaster', slug='toaster', sku='T1',
            short_description='2-slice toaster',
            description='wide slot toaster',
            price=Money(25, 'USD'), status='active',
        )

    def test_keyword_fallback_when_no_embeddings(self):
        results, used = semantic_search('blender', limit=5)
        self.assertFalse(used)
        self.assertIn(self.p1, results)
        self.assertNotIn(self.p2, results)

    def test_used_embedding_when_embeddings_present(self):
        upsert_product_embedding(self.p1)
        upsert_product_embedding(self.p2)
        self.assertTrue(ProductEmbedding.objects.exists())
        results, used = semantic_search('smoothie', limit=2)
        self.assertTrue(used)
        # Result list must be non-empty and ranked
        self.assertGreaterEqual(len(results), 1)

    def test_upsert_is_idempotent_on_unchanged_text(self):
        upsert_product_embedding(self.p1)
        first = ProductEmbedding.objects.get(product=self.p1)
        upsert_product_embedding(self.p1)
        second = ProductEmbedding.objects.get(product=self.p1)
        self.assertEqual(first.updated_at, second.updated_at)
