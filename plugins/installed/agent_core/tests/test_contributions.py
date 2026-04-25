"""Tests for plugin contribution surfaces."""
from __future__ import annotations

from django.test import TestCase

from core.agents import agent_registry


class AgentCoreContributionsTests(TestCase):

    def test_builtin_agents_are_registered(self):
        names = {a.name for a in agent_registry.all_agents()}
        for required in ('concierge', 'merchant_ops', 'pricing', 'content_writer'):
            self.assertIn(required, names, f'missing built-in agent {required}')

    def test_audience_filtering(self):
        storefront = {a.name for a in agent_registry.agents_for_audience('storefront')}
        self.assertIn('concierge', storefront)
        self.assertNotIn('merchant_ops', storefront)
        merchant = {a.name for a in agent_registry.agents_for_audience('merchant')}
        self.assertIn('merchant_ops', merchant)
        self.assertIn('content_writer', merchant)

    def test_builtin_tools_registered(self):
        tool_names = {t.name for t in agent_registry.platform_tools()}
        for required in (
            'catalog.find_products',
            'catalog.get_product',
            'cart.summary',
            'orders.list_recent',
            'analytics.revenue_summary',
            'content.draft_product_description',
        ):
            self.assertIn(required, tool_names, f'missing built-in tool {required}')

    def test_inventory_tools_registered(self):
        names = {t.name for t in agent_registry.platform_tools()}
        self.assertIn('inventory.low_stock_report', names)
        self.assertIn('inventory.adjust_stock', names)

    def test_seo_tools_registered(self):
        names = {t.name for t in agent_registry.platform_tools()}
        self.assertIn('seo.get_meta', names)
        self.assertIn('seo.set_meta', names)

    def test_merchant_ops_sees_inventory_tools_via_scopes(self):
        agent = agent_registry.get_agent('merchant_ops')
        tool_names = {t.name for t in agent.get_tools()}
        # Merchant ops has 'inventory.read' and 'inventory.write' so it should see both inventory tools.
        self.assertIn('inventory.low_stock_report', tool_names)
        self.assertIn('inventory.adjust_stock', tool_names)

    def test_concierge_does_not_see_inventory_writes(self):
        agent = agent_registry.get_agent('concierge')
        tool_names = {t.name for t in agent.get_tools()}
        self.assertNotIn('inventory.adjust_stock', tool_names)
        self.assertNotIn('seo.set_meta', tool_names)
