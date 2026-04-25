"""Built-in tool catalog shipped by agent_core.

Each module groups tools that operate on a domain. They are registered
into `agent_registry` via `AgentCorePlugin.contribute_agent_tools()`.
"""
from __future__ import annotations

from plugins.installed.agent_core.tools.catalog import (
    find_products_tool,
    get_product_tool,
    list_categories_tool,
)
from plugins.installed.agent_core.tools.cart import (
    add_to_cart_tool,
    get_cart_summary_tool,
)
from plugins.installed.agent_core.tools.orders import (
    list_recent_orders_tool,
    summarise_order_tool,
)
from plugins.installed.agent_core.tools.analytics import (
    revenue_summary_tool,
    top_products_tool,
)
from plugins.installed.agent_core.tools.content import (
    draft_product_description_tool,
)


def all_builtin_tools() -> list:
    return [
        find_products_tool,
        get_product_tool,
        list_categories_tool,
        add_to_cart_tool,
        get_cart_summary_tool,
        list_recent_orders_tool,
        summarise_order_tool,
        revenue_summary_tool,
        top_products_tool,
        draft_product_description_tool,
    ]
