"""
AI Assistant — AIContext Middleware
Attaches a rich AI context object to every request.
Resolves customer memory, agent capabilities, experiment assignments.
"""
import logging
from dataclasses import dataclass, field

logger = logging.getLogger('morpheus.ai.context')


@dataclass
class AIContext:
    """Enriched context attached to every request for AI personalisation."""
    customer_id: str | None = None
    agent_id: str | None = None
    agent_capabilities: dict = field(default_factory=dict)
    memories: list[dict] = field(default_factory=list)
    session_intent: str | None = None
    personalization_tier: str = 'none'       # none | basic | full
    experiment_assignments: dict = field(default_factory=dict)
    ab_cohort: str = ''

    @property
    def is_agent(self) -> bool:
        return bool(self.agent_id)

    @property
    def is_personalized(self) -> bool:
        return self.personalization_tier in ('basic', 'full')

    def get_memory_context_string(self) -> str:
        """Format memories as a LLM-readable string."""
        if not self.memories:
            return ''
        lines = []
        for m in self.memories:
            if m.get('confidence', 1.0) > 0.3:
                lines.append(f"- {m['key']}: {m['value']}")
        return '\n'.join(lines)


class AIContextMiddleware:
    """Attaches AIContext to request.ai_context for all views and GraphQL resolvers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.ai_context = self._build_context(request)
        response = self.get_response(request)
        return response

    def _build_context(self, request) -> AIContext:
        ctx = AIContext()

        # ── Agent token auth ───────────────────────────────────────
        agent_token = request.headers.get('X-Agent-Token') or request.headers.get('Authorization', '').replace('AgentToken ', '')
        if agent_token:
            try:
                from plugins.installed.ai_assistant.models import AgentRegistration
                agent = AgentRegistration.objects.get(token=agent_token, is_active=True)
                ctx.agent_id = agent.agent_id
                ctx.agent_capabilities = {
                    'can_browse': agent.can_browse,
                    'can_purchase': agent.can_purchase,
                    'can_manage_inventory': agent.can_manage_inventory,
                    'budget_limit': str(agent.budget_limit_amount),
                    'allowed_categories': agent.allowed_categories,
                }
                ctx.personalization_tier = 'full'
                return ctx
            except Exception:
                pass

        # ── Authenticated customer ─────────────────────────────────
        if request.user.is_authenticated:
            ctx.customer_id = str(request.user.id)
            ctx.personalization_tier = 'full'
            try:
                from plugins.installed.ai_assistant.models import AgentMemory
                memories = AgentMemory.objects.filter(
                    customer=request.user,
                    confidence__gte=0.2,
                ).values('memory_type', 'key', 'value', 'confidence')[:50]
                ctx.memories = list(memories)
            except Exception:
                pass

        # ── Experiment assignment ──────────────────────────────────
        ctx.ab_cohort = request.session.get('ab_cohort', '')
        if not ctx.ab_cohort:
            import random, string
            ctx.ab_cohort = ''.join(random.choices(string.ascii_lowercase, k=8))
            request.session['ab_cohort'] = ctx.ab_cohort

        return ctx
