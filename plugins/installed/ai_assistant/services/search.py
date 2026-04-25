"""
Semantic product search.

Tries embedding-based ranking when ProductEmbedding rows exist, and falls
back to a Postgres full-text / SQLite icontains query otherwise. Always
returns active products only.
"""
from __future__ import annotations

import logging

from django.db.models import Q

from plugins.installed.catalog.models import Product

logger = logging.getLogger('morpheus.ai.search')


def _keyword_fallback(query: str, limit: int) -> list[Product]:
    qs = (
        Product.objects.filter(status='active')
        .filter(
            Q(name__icontains=query)
            | Q(short_description__icontains=query)
            | Q(description__icontains=query)
        )
        .select_related('category', 'vendor')
        .prefetch_related('variants', 'images')
        .distinct()
    )
    products = list(qs[:limit])
    if products:
        return products
    return list(
        Product.objects.filter(status='active', is_featured=True)
        .select_related('category', 'vendor')
        .prefetch_related('variants', 'images')[:limit]
    )


def semantic_search(query: str, limit: int = 8) -> tuple[list[Product], bool]:
    """
    Returns `(products, used_embedding)`.

    used_embedding=True only when at least one ProductEmbedding row exists and
    we computed cosine similarity against an actual query embedding.
    """
    from plugins.installed.ai_assistant.models import ProductEmbedding
    from plugins.installed.ai_assistant.services.embeddings import (
        cosine_similarity,
        embed,
    )

    if not ProductEmbedding.objects.exists():
        return _keyword_fallback(query, limit), False

    try:
        query_vec = embed(query)
    except Exception as e:  # noqa: BLE001 — providers can fail in surprising ways
        logger.warning("Embed query failed (%s); using keyword fallback", e)
        return _keyword_fallback(query, limit), False

    candidate_pool = (
        ProductEmbedding.objects
        .select_related('product', 'product__category', 'product__vendor')
        .prefetch_related('product__variants', 'product__images')
        .filter(product__status='active')
    )
    scored: list[tuple[float, Product]] = []
    for emb in candidate_pool.iterator(chunk_size=500):
        if not emb.vector:
            continue
        scored.append((cosine_similarity(query_vec, emb.vector), emb.product))
    if not scored:
        return _keyword_fallback(query, limit), False

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [p for _, p in scored[:limit]], True


def upsert_product_embedding(product: Product) -> None:
    """Compute and persist the embedding for a single product (idempotent)."""
    import hashlib

    from plugins.installed.ai_assistant.models import ProductEmbedding
    from plugins.installed.ai_assistant.services.embeddings import EMBEDDING_DIM, embed

    text = ' | '.join(filter(None, [
        product.name,
        product.short_description,
        product.description,
        product.category.name if product.category_id else '',
    ]))
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()

    existing = ProductEmbedding.objects.filter(product=product).first()
    if existing and existing.source_text_hash == digest:
        return

    vector = embed(text)
    ProductEmbedding.objects.update_or_create(
        product=product,
        defaults={
            'vector': vector,
            'dim': len(vector) or EMBEDDING_DIM,
            'source_text_hash': digest,
        },
    )
