"""Content Writer — drafts product copy and journal entries."""
from __future__ import annotations

from core.agents import MorpheusAgent, Prompt, prompt_registry

prompt_registry.register(Prompt(
    name='content_writer',
    version=1,
    template=(
        'You are the Content Writer agent for an independent bookstore. '
        'Your prose is literary but unfussy: short sentences, no hype, '
        'no marketing adjectives. When asked to draft a product '
        'description, call `content.draft_product_description` and return '
        'its output verbatim with at most a one-sentence editorial note.'
    ),
))


class ContentWriterAgent(MorpheusAgent):
    name = 'content_writer'
    label = 'Content Writer'
    description = 'Drafts product descriptions, journal entries, marketing copy.'
    icon = 'feather'
    audience = 'merchant'
    scopes = ['catalog.read', 'content.read', 'content.write']
    prompt_name = 'content_writer'
    temperature = 0.6
    max_tokens = 1200
    max_steps = 4
