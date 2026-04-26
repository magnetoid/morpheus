"""
MorpheusAgent — the base class every agent inherits from.

A `MorpheusAgent` is metadata + a default tool list + a system prompt.
It is *not* a runtime — execution is the job of `AgentRuntime`. This
keeps agents trivial to write and trivial to test.

Minimal example::

    from core.agents import MorpheusAgent, Prompt, prompt_registry

    prompt_registry.register(Prompt(
        name='concierge',
        version=1,
        template='You are a friendly bookstore concierge for {store_name}.',
    ))

    class ConciergeAgent(MorpheusAgent):
        name = 'concierge'
        label = 'Storefront Concierge'
        description = 'Helps shoppers find and buy books.'
        scopes = ['catalog.read', 'cart.write']
        prompt_name = 'concierge'
"""
from __future__ import annotations

import logging
import re
from typing import Any

from core.agents.tools import Tool

logger = logging.getLogger('morpheus.agents')

_NAME_RE = re.compile(r'^[a-z][a-z0-9_]*$')


class AgentConfigurationError(TypeError):
    """Raised when an agent's metadata is invalid at class-definition time."""


class MorpheusAgent:
    """Base class for every Morpheus agent."""

    # ── Metadata (override in subclass) ────────────────────────────────────────
    name: str = ''
    label: str = ''
    description: str = ''
    version: str = '1.0.0'
    icon: str = 'sparkles'

    # Visibility — where the agent can be invoked from.
    audience: str = 'merchant'   # 'storefront' | 'merchant' | 'system' | 'any'

    # The capability scopes this agent's tools may declare.
    scopes: list[str] = []

    # System prompt — looked up by name in the prompt registry.
    prompt_name: str = ''
    prompt_version: int | None = None

    # LLM configuration.
    provider: str = ''           # '' = use platform default
    model: str = ''
    temperature: float = 0.3
    max_tokens: int = 1024

    # Runtime guards.
    max_steps: int = 8
    requires_approval: bool = False  # blanket approval gate (per-tool gates also exist)

    # Tools — concrete tool list, populated by `get_tools()` at runtime.
    # Tuple, NOT list, so accidental .append() on the class default raises
    # rather than silently bleeding tools across sibling agent classes.
    default_tools: tuple[Tool, ...] = ()

    # ── Class-time validation ──────────────────────────────────────────────────

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.name:
            return  # intermediate base classes are allowed
        if not _NAME_RE.match(cls.name):
            raise AgentConfigurationError(
                f'{cls.__name__}.name must be snake_case. Got {cls.name!r}.'
            )
        if not cls.label:
            raise AgentConfigurationError(f'{cls.__name__}.label is required.')
        if cls.audience not in ('storefront', 'merchant', 'system', 'any'):
            raise AgentConfigurationError(
                f'{cls.__name__}.audience must be one of '
                "'storefront' | 'merchant' | 'system' | 'any'. "
                f'Got {cls.audience!r}.'
            )
        if not isinstance(cls.scopes, list):
            raise AgentConfigurationError(f'{cls.__name__}.scopes must be a list.')

    # ── Hooks for subclasses ───────────────────────────────────────────────────

    def get_system_prompt(self, context: dict[str, Any] | None = None) -> str:
        """Render the system prompt. Override for dynamic prompts."""
        if not self.prompt_name:
            return self.description or f'You are the {self.label} agent.'
        from core.agents.prompts import prompt_registry
        try:
            prompt = prompt_registry.get(self.prompt_name, self.prompt_version)
        except KeyError:
            return self.description or f'You are the {self.label} agent.'
        return prompt.render(**(context or {}))

    def get_tools(self) -> list[Tool]:
        """Return the tools this agent can call.

        Default: `default_tools` plus any platform tool whose scopes are a
        subset of this agent's scopes (collected from the agent registry).
        Override to filter further or to add per-instance tools.
        """
        from core.agents.registry import agent_registry

        out: list[Tool] = list(self.default_tools or [])
        seen_names = {t.name for t in out}
        for tool in agent_registry.platform_tools():
            if tool.name in seen_names:
                continue
            if tool.scopes and not set(tool.scopes).issubset(set(self.scopes)):
                continue
            out.append(tool)
            seen_names.add(tool.name)
        return out

    def on_run_start(self, *, run, context: dict[str, Any]) -> None:
        """Hook called when a run begins; override for custom prep."""

    def on_run_end(self, *, run, context: dict[str, Any], result) -> None:
        """Hook called when a run ends (success or failure)."""

    def __repr__(self) -> str:
        return f'<MorpheusAgent {self.name} v{self.version}>'
