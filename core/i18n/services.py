"""Translation services — set/get/translated/bulk."""
from __future__ import annotations

import logging
from typing import Iterable, Optional

logger = logging.getLogger('morpheus.i18n')


def _ct(obj):
    from django.contrib.contenttypes.models import ContentType
    return ContentType.objects.get_for_model(type(obj))


def set_translation(obj, field: str, language_code: str, value: str,
                    *, machine_translated: bool = False) -> 'Translation':  # noqa: F821
    from core.i18n.models import Translation
    ct = _ct(obj)
    tr, _ = Translation.objects.update_or_create(
        content_type=ct, object_id=str(obj.pk),
        field=field[:80], language_code=language_code[:10],
        defaults={'value': value, 'is_machine_translated': machine_translated},
    )
    return tr


def get_translation(obj, field: str, language_code: str) -> Optional[str]:
    from core.i18n.models import Translation
    if not language_code:
        return None
    ct = _ct(obj)
    row = Translation.objects.filter(
        content_type=ct, object_id=str(obj.pk),
        field=field, language_code=language_code,
    ).first()
    return row.value if row else None


def translated(obj, field: str, language_code: str = '') -> str:
    """Return translation if present, else fall back to the model value."""
    if language_code:
        val = get_translation(obj, field, language_code)
        if val:
            return val
    return getattr(obj, field, '') or ''


def translations_for(obj, *, language_code: str = '') -> dict[str, str]:
    """All translations for `obj` (optionally filtered by language)."""
    from core.i18n.models import Translation
    ct = _ct(obj)
    qs = Translation.objects.filter(content_type=ct, object_id=str(obj.pk))
    if language_code:
        qs = qs.filter(language_code=language_code)
    return {f'{r.field}@{r.language_code}': r.value for r in qs}


def bulk_set_translations(obj, language_code: str, mapping: dict) -> int:
    """Set multiple field translations at once: `mapping = {field: value}`."""
    n = 0
    for field, val in (mapping or {}).items():
        if val is None or val == '':
            continue
        set_translation(obj, field, language_code, str(val))
        n += 1
    return n
