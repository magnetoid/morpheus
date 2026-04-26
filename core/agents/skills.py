"""Skills — labeled bundles of agent tools + a system-prompt prelude.

A `Skill` is a reusable, named capability pack that an agent can opt into:

    storefront_skill = Skill(
        name='storefront_concierge',
        label='Storefront Concierge',
        description='Read-only access to catalog, cart, recommendations.',
        tools=[search_products_tool, get_product_tool, recommend_tool],
        system_prompt_prelude='You can browse the catalog and recommend products.',
    )

    class ConciergeAgent(MorpheusAgent):
        uses_skills = ['storefront_concierge']

When the runtime resolves an agent's tool list it concatenates the
agent's own `tools` tuple with every Tool from each skill in
`uses_skills`. The agent's `get_system_prompt()` likewise prepends each
skill's `system_prompt_prelude`.

Skills are registered by plugins via `contribute_skills()` and live in a
process-wide `skill_registry`. They're the canonical replacement for
the old "stuff a giant tools tuple on every agent class" pattern.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from core.agents.tools import Tool


@dataclass(frozen=True)
class Skill:
    name: str
    label: str
    description: str = ''
    tools: tuple[Tool, ...] = field(default_factory=tuple)
    system_prompt_prelude: str = ''

    def __post_init__(self):
        if not self.name:
            raise ValueError('Skill.name is required')
        if not self.label:
            object.__setattr__(self, 'label', self.name.replace('_', ' ').title())
        if isinstance(self.tools, list):
            object.__setattr__(self, 'tools', tuple(self.tools))


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        if not isinstance(skill, Skill):
            raise TypeError(f'expected Skill, got {type(skill).__name__}')
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def all(self) -> list[Skill]:
        return list(self._skills.values())

    def resolve(self, names: Iterable[str]) -> list[Skill]:
        out: list[Skill] = []
        for name in (names or []):
            s = self._skills.get(name)
            if s is not None:
                out.append(s)
        return out


skill_registry = SkillRegistry()
