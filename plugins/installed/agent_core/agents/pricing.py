"""Pricing — system agent that reasons about dynamic price adjustments."""
from __future__ import annotations

from core.agents import MorpheusAgent, Prompt, prompt_registry

prompt_registry.register(Prompt(
    name='pricing',
    version=1,
    template=(
        'You are the Pricing agent. Given a product, its category, '
        'recent demand signal, and the current price, decide whether to '
        'recommend a price change. You may only recommend ±15% from the '
        'current price. Reply with strict JSON: '
        '{{"price": <number>, "reason": "<short reason>"}}.'
    ),
))


class PricingAgent(MorpheusAgent):
    name = 'pricing'
    label = 'Pricing'
    description = 'Recommends dynamic price adjustments. Output is advisory.'
    icon = 'tag'
    audience = 'system'
    scopes = ['catalog.read', 'analytics.read']
    prompt_name = 'pricing'
    temperature = 0.0
    max_tokens = 300
    max_steps = 4
