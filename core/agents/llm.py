"""
LLM provider abstraction.

The runtime is provider-agnostic. Each concrete provider implements a
single method — `respond(messages, tools, ...)` — that returns either
"final text" or "I want to call these tools." The runtime drives the
loop; providers just translate.

Built-in providers:
* `OpenAIProvider` — function-calling via the official SDK.
* `AnthropicProvider` — tool-use via the official SDK.
* `OllamaProvider` — local inference (best-effort tool support).
* `MockLLMProvider` — deterministic, used in tests.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable

from django.conf import settings

logger = logging.getLogger('morpheus.agents.llm')


@dataclass(slots=True)
class LLMMessage:
    role: str            # 'system' | 'user' | 'assistant' | 'tool'
    content: str = ''
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list['LLMToolCall'] = field(default_factory=list)


@dataclass(slots=True)
class LLMToolCall:
    """A tool invocation requested by the model."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class LLMResponse:
    text: str = ''
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ''
    raw: Any = None

    @property
    def is_tool_call(self) -> bool:
        return bool(self.tool_calls)


class LLMProvider(ABC):
    """A provider knows how to translate `LLMMessage` + tool list into a response."""

    name: str = 'base'
    model: str = ''

    @abstractmethod
    def respond(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        ...


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI
# ─────────────────────────────────────────────────────────────────────────────


class OpenAIProvider(LLMProvider):
    name = 'openai'

    def __init__(self, model: str | None = None) -> None:
        import openai  # lazy import — provider is only loaded when used
        api_key = getattr(settings, 'OPENAI_API_KEY', '')
        self._client = openai.OpenAI(api_key=api_key) if api_key else openai.OpenAI()
        self.model = model or getattr(settings, 'AI_MODEL', 'gpt-4o-mini')

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            if m.role == 'tool':
                out.append({
                    'role': 'tool',
                    'tool_call_id': m.tool_call_id or '',
                    'content': m.content,
                })
                continue
            entry: dict[str, Any] = {'role': m.role, 'content': m.content}
            if m.tool_calls:
                entry['tool_calls'] = [
                    {
                        'id': tc.id,
                        'type': 'function',
                        'function': {
                            'name': tc.name,
                            'arguments': json.dumps(tc.arguments),
                        },
                    }
                    for tc in m.tool_calls
                ]
            out.append(entry)
        return out

    def respond(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            'model': self.model,
            'messages': self._convert_messages(messages),
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        if tools:
            kwargs['tools'] = [t.to_openai_schema() for t in tools]
        completion = self._client.chat.completions.create(**kwargs)
        choice = completion.choices[0]
        msg = choice.message
        tool_calls: list[LLMToolCall] = []
        for tc in (getattr(msg, 'tool_calls', None) or []):
            try:
                args = json.loads(tc.function.arguments or '{}')
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(LLMToolCall(id=tc.id, name=tc.function.name, arguments=args))
        return LLMResponse(
            text=msg.content or '',
            tool_calls=tool_calls,
            prompt_tokens=getattr(completion.usage, 'prompt_tokens', 0) or 0,
            completion_tokens=getattr(completion.usage, 'completion_tokens', 0) or 0,
            model=self.model,
            raw=completion,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Anthropic
# ─────────────────────────────────────────────────────────────────────────────


class AnthropicProvider(LLMProvider):
    name = 'anthropic'

    def __init__(self, model: str | None = None) -> None:
        import anthropic
        api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = model or getattr(settings, 'AI_MODEL', 'claude-3-5-haiku-latest')

    def _convert(self, messages: list[LLMMessage]) -> tuple[str, list[dict[str, Any]]]:
        system_chunks: list[str] = []
        out: list[dict[str, Any]] = []
        for m in messages:
            if m.role == 'system':
                if m.content:
                    system_chunks.append(m.content)
                continue
            if m.role == 'tool':
                out.append({
                    'role': 'user',
                    'content': [{
                        'type': 'tool_result',
                        'tool_use_id': m.tool_call_id or '',
                        'content': m.content,
                    }],
                })
                continue
            if m.role == 'assistant' and m.tool_calls:
                blocks: list[dict[str, Any]] = []
                if m.content:
                    blocks.append({'type': 'text', 'text': m.content})
                for tc in m.tool_calls:
                    blocks.append({
                        'type': 'tool_use',
                        'id': tc.id,
                        'name': tc.name,
                        'input': tc.arguments,
                    })
                out.append({'role': 'assistant', 'content': blocks})
                continue
            out.append({'role': m.role, 'content': m.content})
        return '\n\n'.join(system_chunks), out

    def respond(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        system, msgs = self._convert(messages)
        kwargs: dict[str, Any] = {
            'model': self.model,
            'messages': msgs,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        if system:
            kwargs['system'] = system
        if tools:
            kwargs['tools'] = [t.to_anthropic_schema() for t in tools]
        resp = self._client.messages.create(**kwargs)

        text_chunks: list[str] = []
        tool_calls: list[LLMToolCall] = []
        for block in resp.content or []:
            btype = getattr(block, 'type', '')
            if btype == 'text':
                text_chunks.append(getattr(block, 'text', '') or '')
            elif btype == 'tool_use':
                tool_calls.append(LLMToolCall(
                    id=getattr(block, 'id', ''),
                    name=getattr(block, 'name', ''),
                    arguments=getattr(block, 'input', {}) or {},
                ))
        usage = getattr(resp, 'usage', None)
        return LLMResponse(
            text='\n'.join(text_chunks),
            tool_calls=tool_calls,
            prompt_tokens=getattr(usage, 'input_tokens', 0) or 0,
            completion_tokens=getattr(usage, 'output_tokens', 0) or 0,
            model=self.model,
            raw=resp,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Ollama (best-effort, no native tool calls)
# ─────────────────────────────────────────────────────────────────────────────


class OllamaProvider(LLMProvider):
    name = 'ollama'

    def __init__(self, model: str | None = None) -> None:
        import requests
        self._requests = requests
        self.base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = model or getattr(settings, 'AI_MODEL', 'llama3.2')

    def respond(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        # Best-effort: fold system + history into a single prompt.
        prompt_parts: list[str] = []
        for m in messages:
            tag = m.role.upper()
            prompt_parts.append(f'[{tag}]\n{m.content}')
        prompt = '\n\n'.join(prompt_parts)
        if tools:
            tool_specs = '\n'.join(f'- {t.name}: {t.description}' for t in tools)
            prompt += '\n\n[TOOLS AVAILABLE]\n' + tool_specs
        resp = self._requests.post(
            f'{self.base_url}/api/generate',
            json={
                'model': self.model,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': temperature, 'num_predict': max_tokens},
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return LLMResponse(text=data.get('response', ''), model=self.model, raw=data)


# ─────────────────────────────────────────────────────────────────────────────
# Mock — deterministic, used in tests + when no provider configured
# ─────────────────────────────────────────────────────────────────────────────


class MockLLMProvider(LLMProvider):
    """Scripted provider for tests.

    Construct with a list of `LLMResponse` objects; each `respond()` call
    pops the next response. Useful for asserting tool-call sequences.
    """

    name = 'mock'

    def __init__(
        self,
        responses: Iterable[LLMResponse] | None = None,
        *,
        echo_user: bool = True,
    ) -> None:
        self.model = 'mock-1'
        self._responses: list[LLMResponse] = list(responses or [])
        self._echo_user = echo_user
        self.calls: list[dict[str, Any]] = []

    def push(self, response: LLMResponse) -> None:
        self._responses.append(response)

    def respond(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[Any] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        self.calls.append({'messages': list(messages), 'tools': list(tools or [])})
        if self._responses:
            r = self._responses.pop(0)
            r.model = r.model or self.model
            return r
        if self._echo_user:
            last_user = next((m.content for m in reversed(messages) if m.role == 'user'), '')
            return LLMResponse(text=f'OK: {last_user[:200]}', model=self.model)
        return LLMResponse(text='', model=self.model)


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────


def get_llm_provider(name: str | None = None, *, model: str | None = None) -> LLMProvider:
    """Resolve a provider by name. Falls back to `MockLLMProvider` if unconfigured."""
    chosen = (name or getattr(settings, 'AI_PROVIDER', '')).strip().lower()
    if chosen == 'openai':
        try:
            return OpenAIProvider(model=model)
        except Exception as e:  # noqa: BLE001
            logger.warning('openai provider unavailable, using mock: %s', e)
            return MockLLMProvider()
    if chosen == 'anthropic':
        try:
            return AnthropicProvider(model=model)
        except Exception as e:  # noqa: BLE001
            logger.warning('anthropic provider unavailable, using mock: %s', e)
            return MockLLMProvider()
    if chosen == 'ollama':
        try:
            return OllamaProvider(model=model)
        except Exception as e:  # noqa: BLE001
            logger.warning('ollama provider unavailable, using mock: %s', e)
            return MockLLMProvider()
    return MockLLMProvider()
