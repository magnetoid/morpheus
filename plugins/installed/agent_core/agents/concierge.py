"""Concierge — storefront-facing chat agent."""
from __future__ import annotations

from core.agents import MorpheusAgent, Prompt, prompt_registry

prompt_registry.register(Prompt(
    name='concierge',
    version=1,
    template=(
        'You are the Concierge for an independent online bookstore. '
        'Your job is to help shoppers find books they will love and add '
        'them to their cart. Be warm, brief, and concrete. When you '
        'recommend books, call `catalog.find_products`. When the shopper '
        'wants to buy, call `cart.add_item` with the product slug. '
        'Never invent products — only recommend titles returned by the '
        'tools. Reply in 1–3 short paragraphs.'
    ),
    description='System prompt for the storefront concierge.',
))


class ConciergeAgent(MorpheusAgent):
    name = 'concierge'
    label = 'Storefront Concierge'
    description = 'Helps shoppers discover and buy books.'
    icon = 'message-circle'
    audience = 'storefront'
    scopes = ['catalog.read', 'cart.read', 'cart.write']
    prompt_name = 'concierge'
    temperature = 0.5
    max_tokens = 800
    max_steps = 6
