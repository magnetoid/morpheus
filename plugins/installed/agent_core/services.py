"""
agent_core services — bridge between the kernel runtime and persistence.

The kernel `AgentRuntime` doesn't know about Django models. This module
wraps a run with two responsibilities:

1. Mirror every TraceStep into AgentStep rows (lossless audit).
2. Update the AgentRun row with final state, tokens, duration.

It also provides helpers for the chat surface: persisting conversations,
loading message history, dispatching runs to Celery for proactive agents.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Iterable

from django.db import DatabaseError, transaction
from django.utils import timezone

from core.agents import (
    AgentRuntime,
    AgentTrace,
    LLMMessage,
    MorpheusAgent,
    RunResult,
    TraceStep,
    agent_registry,
    get_llm_provider,
)

logger = logging.getLogger('morpheus.agents.services')


def _persist_step(*, run, seq: int, step: TraceStep) -> None:
    from plugins.installed.agent_core.models import AgentStep

    output = step.output
    if output is not None and not isinstance(output, (dict, list, str, int, float, bool)):
        output = str(output)
    AgentStep.objects.create(
        run=run,
        seq=seq,
        kind=step.kind,
        name=step.name,
        content=step.content[:20_000] if step.content else '',
        arguments=step.arguments or {},
        output={'value': output} if output is not None and not isinstance(output, dict) else (output or {}),
        metadata=step.metadata or {},
    )


def run_agent(
    *,
    agent_name: str,
    user_message: str,
    customer: Any | None = None,
    session_key: str = '',
    history: Iterable[LLMMessage] | None = None,
    context: dict[str, Any] | None = None,
    conversation_id: str | None = None,
    on_step: Any = None,
) -> RunResult:
    """Run a registered agent and persist the trace.

    Returns the in-memory `RunResult` so callers can stream the final
    text + steps; the database mirror is updated as the run progresses.
    """
    agent: MorpheusAgent | None = agent_registry.get_agent(agent_name)
    if agent is None:
        raise LookupError(f'Unknown agent: {agent_name}')

    from plugins.installed.agent_core.models import (
        AgentConversation, AgentMessage, AgentRun,
    )

    customer_obj = customer if (customer is not None and getattr(customer, 'is_authenticated', False)) else None

    try:
        run = AgentRun.objects.create(
            agent_name=agent.name,
            audience=agent.audience,
            customer=customer_obj,
            session_key=session_key[:64],
            user_message=user_message[:50_000],
            state='running',
            metadata=context.get('metadata', {}) if context else {},
        )
    except DatabaseError as e:
        logger.warning('agent_core: AgentRun create failed, running in-memory: %s', e)
        run = None

    # Subscriber → mirror into DB live.
    seq_counter = {'i': 0}
    db_subscriber = None
    if run is not None:
        def _mirror(step: TraceStep) -> None:
            seq_counter['i'] += 1
            try:
                _persist_step(run=run, seq=seq_counter['i'], step=step)
            except DatabaseError as e:  # noqa: BLE001
                logger.warning('agent_core: persist step failed: %s', e)
            if on_step is not None:
                try:
                    on_step(step)
                except Exception:  # noqa: BLE001
                    pass
        db_subscriber = _mirror

    provider = get_llm_provider(agent.provider, model=agent.model or None)
    runtime = AgentRuntime(
        agent,
        provider=provider,
        on_step=db_subscriber or on_step,
    )

    started = time.monotonic()
    try:
        result = runtime.run(
            user_message=user_message,
            history=list(history or []),
            context={**(context or {}), 'customer': customer_obj},
            run_id=str(run.id) if run else None,
        )
    except Exception as e:  # noqa: BLE001 — final safety net
        logger.error('agent_core: runtime crashed: %s', e, exc_info=True)
        if run is not None:
            run.state = 'failed'
            run.error = f'{type(e).__name__}: {e}'
            run.ended_at = timezone.now()
            run.save(update_fields=['state', 'error', 'ended_at'])
        raise

    duration_ms = int((time.monotonic() - started) * 1000)

    if run is not None:
        run.state = result.state
        run.final_text = (result.text or '')[:50_000]
        run.error = (result.error or '')[:5_000]
        run.tool_call_count = result.tool_calls
        run.prompt_tokens = result.trace.prompt_tokens
        run.completion_tokens = result.trace.completion_tokens
        run.duration_ms = duration_ms
        run.provider = provider.name
        run.model = provider.model or ''
        run.ended_at = timezone.now()
        run.save(update_fields=[
            'state', 'final_text', 'error', 'tool_call_count',
            'prompt_tokens', 'completion_tokens', 'duration_ms',
            'provider', 'model', 'ended_at',
        ])

    if conversation_id and run is not None:
        try:
            with transaction.atomic():
                conv = AgentConversation.objects.get(id=conversation_id)
                AgentMessage.objects.create(
                    conversation=conv, run=run, role='user', content=user_message[:20_000],
                )
                if result.text:
                    AgentMessage.objects.create(
                        conversation=conv, run=run, role='assistant', content=result.text[:20_000],
                    )
                conv.last_message_at = timezone.now()
                conv.save(update_fields=['last_message_at'])
        except (AgentConversation.DoesNotExist, DatabaseError) as e:
            logger.warning('agent_core: conversation persist failed: %s', e)

    return result


def history_for_conversation(conversation_id: str, *, limit: int = 20) -> list[LLMMessage]:
    """Load the recent messages of a conversation as `LLMMessage` history."""
    from plugins.installed.agent_core.models import AgentMessage

    try:
        rows = list(
            AgentMessage.objects
            .filter(conversation_id=conversation_id)
            .order_by('-created_at')[:limit]
        )
    except DatabaseError as e:
        logger.warning('agent_core: load history failed: %s', e)
        return []
    rows.reverse()
    return [LLMMessage(role=r.role, content=r.content) for r in rows]
