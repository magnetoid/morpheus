"""Content tools — drafting product copy via the LLM gateway."""
from __future__ import annotations

from core.agents import ToolError, ToolResult, get_llm_provider, tool
from core.agents.llm import LLMMessage


@tool(
    name='content.draft_product_description',
    description='Generate a 60–120 word product description for a product (by slug).',
    scopes=['content.write'],
    schema={
        'type': 'object',
        'properties': {
            'slug': {'type': 'string'},
            'tone': {'type': 'string', 'enum': ['neutral', 'literary', 'witty', 'minimal'], 'default': 'literary'},
        },
        'required': ['slug'],
    },
    requires_approval=True,  # writes are approval-gated by default
)
def draft_product_description_tool(*, slug: str, tone: str = 'literary') -> ToolResult:
    from plugins.installed.catalog.models import Product

    try:
        p = Product.objects.get(slug=slug)
    except Product.DoesNotExist as e:
        raise ToolError(f'Unknown product: {slug}') from e

    provider = get_llm_provider()
    msgs = [
        LLMMessage(role='system', content=(
            f'You are a {tone} bookshop copywriter. Write a 60–120 word product '
            'description. Avoid spoilers, hype, and generic adjectives.'
        )),
        LLMMessage(role='user', content=(
            f'Product: {p.name}\n'
            f'Category: {p.category.name if p.category_id else ""}\n'
            f'Existing short: {p.short_description or ""}\n'
            f'Existing long: {(p.description or "")[:1200]}'
        )),
    ]
    resp = provider.respond(messages=msgs, tools=None, temperature=0.6, max_tokens=400)
    return ToolResult(
        output={'product_slug': slug, 'draft': resp.text},
        display=f'Draft for {p.name}',
        metadata={'tokens_in': resp.prompt_tokens, 'tokens_out': resp.completion_tokens},
    )
