"""
Embedding service.

Resolves an embedding provider based on `settings.AI_PROVIDER` and
`settings.AI_EMBEDDING_MODEL`. Always returns a fixed-dimension list of
floats so the rest of the system never has to know which backend was used.

When no provider is configured (CI, local dev with no keys), falls back to a
deterministic hash-based embedding so the rest of the pipeline still works.
This is INTENTIONAL — we want callers to be able to test the full retrieval
flow without paying for tokens.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Sequence

from django.conf import settings

logger = logging.getLogger('morpheus.ai.embeddings')

# Dimension of the deterministic fallback. Real providers will return their
# own dimensions; we keep them in pgvector columns sized to match the chosen
# provider in production. 384 is small enough to be cheap, big enough to be
# meaningful.
EMBEDDING_DIM = 384


def _hash_embedding(text: str) -> list[float]:
    """Deterministic, provider-free embedding for tests + cold dev environments."""
    h = hashlib.sha512(text.encode('utf-8')).digest()
    # Stretch the 64-byte digest into EMBEDDING_DIM floats in [-1, 1].
    raw = (h * ((EMBEDDING_DIM + len(h) - 1) // len(h)))[:EMBEDDING_DIM]
    return [(b - 128) / 128.0 for b in raw]


def embed(text: str) -> list[float]:
    """Embed a single string. Falls back gracefully on provider failure."""
    text = (text or '').strip()
    if not text:
        return [0.0] * EMBEDDING_DIM

    provider = getattr(settings, 'AI_PROVIDER', 'openai')
    model = getattr(settings, 'AI_EMBEDDING_MODEL', 'text-embedding-3-small')

    if provider == 'openai' and getattr(settings, 'OPENAI_API_KEY', ''):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            resp = client.embeddings.create(model=model, input=text)
            return list(resp.data[0].embedding)
        except Exception as e:  # noqa: BLE001 — fall back to deterministic hash, log warning
            logger.warning("OpenAI embed failed (%s); using fallback", e)

    return _hash_embedding(text)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity in pure Python — used for the fallback path."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
