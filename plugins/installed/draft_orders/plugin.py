"""Draft Orders plugin manifest."""
from __future__ import annotations

import logging

from plugins.base import MorpheusPlugin
from plugins.contributions import DashboardPage

logger = logging.getLogger('morpheus.draft_orders')


class DraftOrdersPlugin(MorpheusPlugin):
    name = 'draft_orders'
    label = 'Draft Orders'
    version = '1.0.0'
    description = (
        'Staff-built draft orders / quotes that can be priced, shared with '
        'the customer, then converted to a real order on payment.'
    )
    has_models = True
    requires = ['orders']

    def ready(self) -> None:
        self.register_urls(
            'plugins.installed.draft_orders.urls',
            prefix='dashboard/draft-orders/',
            namespace='draft_orders',
        )

    def contribute_agent_tools(self) -> list:
        from plugins.installed.draft_orders.agent_tools import (
            convert_draft_tool, list_drafts_tool,
        )
        return [list_drafts_tool, convert_draft_tool]

    def contribute_dashboard_pages(self) -> list:
        return [
            DashboardPage(
                slug='index',
                label='Draft orders',
                section='sales',
                icon='file-text',
                view='plugins.installed.draft_orders.views.index',
                order=20,
            ),
        ]
