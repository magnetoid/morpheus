"""Merchant Ops — admin-facing 'do my work' agent."""
from __future__ import annotations

from core.agents import MorpheusAgent, Prompt, prompt_registry

prompt_registry.register(Prompt(
    name='merchant_ops',
    version=1,
    template=(
        'You are the Merchant Ops agent for the Morpheus commerce platform. '
        'You operate the store on behalf of the merchant: querying analytics, '
        'inspecting orders, surfacing low-stock items, and drafting content. '
        'You never invent numbers — always call the right tool. When you '
        'finish a task, summarise what you did in 4–8 bullet points and '
        'flag anything that needs human review. Be terse.'
    ),
))


class MerchantOpsAgent(MorpheusAgent):
    name = 'merchant_ops'
    label = 'Merchant Ops'
    description = 'Drives the store on the merchant\'s behalf — analytics, inventory, content.'
    icon = 'briefcase'
    audience = 'merchant'
    scopes = [
        'catalog.read', 'catalog.write',
        'orders.read',
        'inventory.read', 'inventory.write',
        'analytics.read',
        'content.read', 'content.write',
        'seo.read', 'seo.write',
    ]
    prompt_name = 'merchant_ops'
    temperature = 0.2
    max_tokens = 1200
    max_steps = 12
    requires_approval = False  # individual write tools still gate approval
