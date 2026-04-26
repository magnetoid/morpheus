"""Delegate tools — the Assistant routes requests to specialised agents."""
from __future__ import annotations

from core.assistant.tools.filesystem import ToolError, ToolResult, tool


@tool(
    name='delegate.list_agents',
    description='List every specialised agent the Assistant can delegate to.',
    scopes=['system.read'],
    schema={'type': 'object', 'properties': {}},
)
def list_available_agents_tool() -> ToolResult:
    try:
        from core.agents import agent_registry
    except Exception as e:  # noqa: BLE001
        return ToolResult(output={'agents': [], 'note': f'agent kernel unavailable: {e}'})
    rows = [
        {'name': a.name, 'label': a.label, 'audience': a.audience,
         'description': a.description}
        for a in agent_registry.all_agents()
    ]
    rows.sort(key=lambda r: r['name'])
    return ToolResult(output={'agents': rows}, display=f'{len(rows)} agent(s)')


@tool(
    name='delegate.invoke_agent',
    description=(
        'Hand a task to a specialised agent and return its final answer. '
        'Use this when the user asks for something an agent owns: pricing → '
        '`pricing`, order issues → `support` or `account_manager`, copy → '
        '`content_writer`, store ops (analytics/CRM) → `merchant_ops`, '
        'storefront browsing → `concierge`.'
    ),
    scopes=['system.write'],
    schema={
        'type': 'object',
        'properties': {
            'agent_name': {'type': 'string'},
            'objective': {'type': 'string', 'description': 'What you want the agent to do.'},
        },
        'required': ['agent_name', 'objective'],
    },
)
def invoke_agent_tool(*, agent_name: str, objective: str) -> ToolResult:
    try:
        from core.agents import agent_registry
        from plugins.installed.agent_core.services import run_agent
    except Exception as e:  # noqa: BLE001
        raise ToolError(f'agent layer unavailable: {e}') from e
    if agent_registry.get_agent(agent_name) is None:
        raise ToolError(f'unknown agent: {agent_name}')
    try:
        result = run_agent(
            agent_name=agent_name,
            user_message=objective[:10_000],
            context={'source': 'assistant'},
        )
    except Exception as e:  # noqa: BLE001
        raise ToolError(f'agent run failed: {e}') from e
    return ToolResult(
        output={
            'agent': agent_name, 'state': result.state, 'text': result.text,
            'tool_calls': result.tool_calls,
        },
        display=f'{agent_name}: {result.text[:120]}…' if len(result.text) > 120 else f'{agent_name}: {result.text}',
    )
