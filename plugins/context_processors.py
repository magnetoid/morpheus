"""Plugin context processor — exposes active plugins + dashboard contributions."""
from __future__ import annotations

from collections import OrderedDict


# Section display order in the admin sidebar. Sections not in this list
# fall through to alphabetical order at the bottom.
_SECTION_ORDER = [
    'plugins',
    'sales',
    'marketplace',
    'marketing',
    'crm',
    'growth',      # affiliates / loyalty
    'ai',          # agent_core / Concierge / Ops
    'developer',   # webhooks_ui / functions
    'settings',
    'apps',
]

_SECTION_LABELS = {
    'plugins': 'Plugins',
    'sales': 'Sales',
    'marketplace': 'Marketplace',
    'marketing': 'Marketing',
    'crm': 'CRM',
    'growth': 'Growth',
    'ai': 'AI & agents',
    'developer': 'Developer',
    'settings': 'Settings',
    'apps': 'Apps',
}


def plugin_context(request):
    from plugins.registry import plugin_registry

    pages = plugin_registry.dashboard_pages()

    # Group by section.
    by_section: dict[str, list] = {}
    for page in pages:
        by_section.setdefault(page.section or 'plugins', []).append(page)

    grouped: OrderedDict[str, list] = OrderedDict()
    for key in _SECTION_ORDER:
        if key in by_section:
            grouped[key] = by_section.pop(key)
    for key in sorted(by_section.keys()):
        grouped[key] = by_section[key]

    sidebar_sections = [
        {
            'key': key,
            'label': _SECTION_LABELS.get(key, key.replace('_', ' ').title()),
            'pages': pages_in_section,
        }
        for key, pages_in_section in grouped.items()
    ]

    return {
        'active_plugins': plugin_registry._active,
        'plugin_registry': plugin_registry,
        'dashboard_pages': pages,           # back-compat flat list
        'sidebar_sections': sidebar_sections,  # grouped + ordered
    }
