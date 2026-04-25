"""
agent_core HTTP views.

* `/api/agents/<name>/invoke` — POST a user message, get a JSON RunResult.
* `/api/agents/<name>/stream` — POST + Server-Sent Events for live runs.
* `/dashboard/agents/` — list runs.
* `/dashboard/agents/<run_id>/` — single run trace.
"""
from __future__ import annotations

import json
import logging
from queue import Empty, Queue
from threading import Thread
from typing import Any

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.agents import agent_registry
from plugins.installed.agent_core.services import (
    history_for_conversation,
    run_agent,
)

logger = logging.getLogger('morpheus.agents.views')


def _decode_body(request) -> dict[str, Any]:
    if request.content_type == 'application/json':
        try:
            return json.loads(request.body or b'{}')
        except json.JSONDecodeError:
            return {}
    return dict(request.POST.items())


@csrf_exempt
@require_http_methods(['POST'])
def invoke_agent_view(request, agent_name: str):
    if agent_registry.get_agent(agent_name) is None:
        return JsonResponse({'error': f'Unknown agent: {agent_name}'}, status=404)
    body = _decode_body(request)
    message = (body.get('message') or '').strip()
    if not message:
        return HttpResponseBadRequest('Missing `message`.')

    conversation_id = body.get('conversation_id')
    history = history_for_conversation(conversation_id) if conversation_id else None

    try:
        result = run_agent(
            agent_name=agent_name,
            user_message=message[:10_000],
            customer=getattr(request, 'user', None),
            session_key=getattr(getattr(request, 'session', None), 'session_key', '') or '',
            history=history,
            context={'request': request},
            conversation_id=conversation_id,
        )
    except LookupError as e:
        return JsonResponse({'error': str(e)}, status=404)

    return JsonResponse({
        'run_id': result.run_id,
        'state': result.state,
        'text': result.text,
        'tool_calls': result.tool_calls,
        'tokens': {
            'prompt': result.trace.prompt_tokens,
            'completion': result.trace.completion_tokens,
        },
        'error': result.error or '',
    })


@csrf_exempt
@require_http_methods(['POST'])
def stream_agent_view(request, agent_name: str):
    """Server-Sent Events: live trace of a single run.

    The runtime executes on a worker thread; the view drains a queue and
    writes one event per `TraceStep` until the run finishes.
    """
    if agent_registry.get_agent(agent_name) is None:
        return JsonResponse({'error': f'Unknown agent: {agent_name}'}, status=404)
    body = _decode_body(request)
    message = (body.get('message') or '').strip()
    if not message:
        return HttpResponseBadRequest('Missing `message`.')

    conversation_id = body.get('conversation_id')
    history = history_for_conversation(conversation_id) if conversation_id else None

    queue: Queue = Queue()
    final_box: dict[str, Any] = {}

    def _on_step(step):
        try:
            queue.put({
                'kind': step.kind,
                'name': step.name,
                'content': step.content,
                'arguments': step.arguments,
            })
        except Exception:  # noqa: BLE001
            pass

    def _runner():
        try:
            result = run_agent(
                agent_name=agent_name,
                user_message=message[:10_000],
                customer=getattr(request, 'user', None),
                session_key=getattr(getattr(request, 'session', None), 'session_key', '') or '',
                history=history,
                context={'request': request},
                conversation_id=conversation_id,
                on_step=_on_step,
            )
            final_box['result'] = result
        except Exception as e:  # noqa: BLE001
            final_box['error'] = str(e)
        finally:
            queue.put({'__done__': True})

    Thread(target=_runner, daemon=True).start()

    def _events():
        while True:
            try:
                event = queue.get(timeout=60)
            except Empty:
                yield ': keepalive\n\n'
                continue
            if event.get('__done__'):
                if 'result' in final_box:
                    payload = json.dumps({
                        'state': final_box['result'].state,
                        'text': final_box['result'].text,
                        'run_id': final_box['result'].run_id,
                    })
                    yield f'event: final\ndata: {payload}\n\n'
                else:
                    yield f'event: error\ndata: {json.dumps({"error": final_box.get("error", "")})}\n\n'
                return
            yield f'event: step\ndata: {json.dumps(event)}\n\n'

    response = StreamingHttpResponse(_events(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@require_http_methods(['GET'])
def list_agents_view(request):
    """Public catalog: which agents are registered, their audience + description."""
    out = []
    for a in agent_registry.all_agents():
        out.append({
            'name': a.name,
            'label': a.label,
            'description': a.description,
            'audience': a.audience,
            'icon': a.icon,
            'scopes': list(a.scopes),
        })
    return JsonResponse({'agents': out})


@staff_member_required
def runs_dashboard_view(request):
    from plugins.installed.agent_core.models import AgentRun

    runs = AgentRun.objects.all().order_by('-started_at')[:100]
    return render(request, 'agent_core/dashboard/runs.html', {
        'runs': runs,
        'agents': agent_registry.all_agents(),
        'active_nav': 'agents',
    })


@staff_member_required
def run_detail_view(request, run_id: str):
    from plugins.installed.agent_core.models import AgentRun

    run = get_object_or_404(AgentRun, id=run_id)
    return render(request, 'agent_core/dashboard/run_detail.html', {
        'run': run,
        'steps': run.steps.all().order_by('seq'),
        'active_nav': 'agents',
    })


@staff_member_required
def merchant_ops_chat_view(request):
    """The Merchant Ops chat console (admin only)."""
    return render(request, 'agent_core/dashboard/console.html', {
        'agent_name': 'merchant_ops',
        'active_nav': 'agents',
    })
