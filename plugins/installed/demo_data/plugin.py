"""Demo data plugin manifest."""
from __future__ import annotations

from plugins.base import MorpheusPlugin


class DemoDataPlugin(MorpheusPlugin):
    name = 'demo_data'
    label = 'Demo Data'
    version = '0.1.0'
    description = (
        'Idempotent seed data for the bookstore demo: books, categories, '
        'collections, customers, orders. Provides `manage.py morph_seed_demo`.'
    )
    has_models = False
    requires_plugins: list[str] = []  # Pure CLI; no Django-level deps at boot

    def ready(self) -> None:
        # Nothing to register; the management command is auto-discovered.
        pass
