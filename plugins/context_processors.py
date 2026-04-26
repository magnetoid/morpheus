"""Plugin context processor — exposes active plugins + dashboard contributions."""
from __future__ import annotations

from collections import OrderedDict


# Section display order in the admin sidebar — Shopify-style top-to-bottom.
# Sections not in this list fall through to alphabetical order at the bottom.
_SECTION_ORDER = [
    'ai',           # AI & agents — Morpheus's defining surface; goes at the top
    'sales',        # Orders, Draft orders
    'catalog',      # Products, Bulk CSV, Demo data
    'crm',          # Leads, Accounts, Deals, Tasks
    'marketing',    # Campaigns, Promotions, Coupons
    'cms',          # Pages, Blocks, Menus, Forms
    'analytics',    # Sessions, Events, Funnels
    'seo',          # SEO audit, redirects, JSON-LD config
    'growth',       # Affiliates, loyalty
    'marketplace',  # Vendor onboarding, splits, payouts
    'developer',    # Webhooks UI, Functions
    'plugins',      # uncategorised plugin pages
    'settings',     # RBAC, settings-adjacent operational pages
    'apps',         # the Apps catalog page
]

_SECTION_LABELS = {
    'ai': 'AI & agents',
    'sales': 'Sales',
    'catalog': 'Catalog',
    'crm': 'Customers & CRM',
    'marketing': 'Marketing',
    'cms': 'Content',
    'analytics': 'Analytics',
    'seo': 'SEO',
    'growth': 'Growth',
    'marketplace': 'Marketplace',
    'developer': 'Developer',
    'plugins': 'More plugins',
    'settings': 'Access & roles',
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
        'dashboard_pages': pages,             # back-compat flat list
        'sidebar_sections': sidebar_sections,  # grouped + ordered
        # Template-safe accessor for the unified Settings sidebar.
        'plugin_settings_panels': plugin_registry.all_settings_panels(),
    }
