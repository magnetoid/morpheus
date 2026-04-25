"""
AI Assistant — LLM Gateway
Swappable provider: OpenAI | Anthropic | Ollama | Plugin-custom
Every call is automatically logged to AIInteraction.
"""
import time
import logging
from abc import ABC, abstractmethod
from django.conf import settings

logger = logging.getLogger('morpheus.ai.llm')


class LLMGateway(ABC):
    """Abstract base — all providers implement this interface."""

    model: str = ''

    @abstractmethod
    def complete(self, prompt: str, system: str = '', temperature: float = 0.7,
                 max_tokens: int = 1000, **kwargs) -> str: ...

    @abstractmethod
    def embed(self, text: str) -> list[float]: ...

    def stream(self, prompt: str, system: str = '', **kwargs):
        """Default: non-streaming fallback."""
        yield self.complete(prompt, system=system, **kwargs)

    def _log(self, interaction_type: str, prompt: str, result: str,
             prompt_tokens: int, completion_tokens: int, cost_usd: float,
             latency_ms: int, success: bool = True, error: str = '',
             **context):
        """Log every AI call to AIInteraction. Never raises."""
        try:
            from plugins.installed.ai_assistant.models import AIInteraction
            AIInteraction.objects.create(
                interaction_type=interaction_type,
                model_used=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                input_data={'prompt': prompt[:2000]},
                output_data={'result': result[:2000]},
                success=success,
                error_message=error,
                **{k: v for k, v in context.items() if k in ('customer', 'product', 'order', 'agent_id')},
            )
        except Exception as e:
            logger.error(f"Failed to log AIInteraction: {e}")


class OpenAIGateway(LLMGateway):
    def __init__(self):
        import openai
        from plugins.registry import plugin_registry
        ai_plugin = plugin_registry.get_plugin('ai_assistant')
        api_key = ai_plugin.get_config_value('openai_api_key') or settings.OPENAI_API_KEY
        self.client = openai.OpenAI(api_key=api_key)
        self.model = settings.AI_MODEL
        self.embed_model = settings.AI_EMBEDDING_MODEL

    def complete(self, prompt: str, system: str = '', temperature: float = 0.7,
                 max_tokens: int = 1000, **kwargs) -> str:
        messages = []
        if system:
            messages.append({'role': 'system', 'content': system})
        messages.append({'role': 'user', 'content': prompt})

        start = time.monotonic()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result = response.choices[0].message.content
            elapsed = int((time.monotonic() - start) * 1000)
            usage = response.usage
            cost = self._estimate_cost(usage.prompt_tokens, usage.completion_tokens)
            self._log('completion', prompt, result,
                      usage.prompt_tokens, usage.completion_tokens, cost, elapsed)
            return result
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            self._log('completion', prompt, '', 0, 0, 0, elapsed, success=False, error=str(e))
            logger.error(f"OpenAI completion error: {e}")
            raise

    def embed(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.embed_model, input=text)
        return response.data[0].embedding

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        # GPT-4o-mini pricing (update as needed)
        prices = {
            'gpt-4o': (0.005, 0.015),
            'gpt-4o-mini': (0.00015, 0.0006),
            'gpt-3.5-turbo': (0.0005, 0.0015),
        }
        p_in, p_out = prices.get(self.model, (0.001, 0.003))
        return (prompt_tokens / 1000 * p_in) + (completion_tokens / 1000 * p_out)


class AnthropicGateway(LLMGateway):
    def __init__(self):
        import anthropic
        from plugins.registry import plugin_registry
        ai_plugin = plugin_registry.get_plugin('ai_assistant')
        api_key = ai_plugin.get_config_value('anthropic_api_key') or settings.ANTHROPIC_API_KEY
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = settings.AI_MODEL or 'claude-3-5-haiku-latest'

    def complete(self, prompt: str, system: str = '', temperature: float = 0.7,
                 max_tokens: int = 1000, **kwargs) -> str:
        start = time.monotonic()
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system or 'You are a helpful ecommerce assistant.',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=temperature,
            )
            result = response.content[0].text
            elapsed = int((time.monotonic() - start) * 1000)
            self._log('completion', prompt, result,
                      response.usage.input_tokens, response.usage.output_tokens, 0.0, elapsed)
            return result
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            self._log('completion', prompt, '', 0, 0, 0, elapsed, success=False, error=str(e))
            raise

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError("Anthropic does not provide embeddings; use OpenAI or Ollama.")


class OllamaGateway(LLMGateway):
    """Local Ollama instance — full privacy, no data leaves the server."""

    def __init__(self):
        import requests
        self.requests = requests
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.AI_MODEL or 'llama3.2'

    def complete(self, prompt: str, system: str = '', temperature: float = 0.7,
                 max_tokens: int = 1000, **kwargs) -> str:
        start = time.monotonic()
        try:
            resp = self.requests.post(f'{self.base_url}/api/generate', json={
                'model': self.model,
                'prompt': f"{system}\n\n{prompt}" if system else prompt,
                'stream': False,
                'options': {'temperature': temperature, 'num_predict': max_tokens},
            }, timeout=120)
            resp.raise_for_status()
            result = resp.json().get('response', '')
            elapsed = int((time.monotonic() - start) * 1000)
            self._log('completion', prompt, result, 0, 0, 0.0, elapsed)
            return result
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise

    def embed(self, text: str) -> list[float]:
        resp = self.requests.post(f'{self.base_url}/api/embeddings', json={
            'model': self.model, 'prompt': text
        }, timeout=30)
        resp.raise_for_status()
        return resp.json().get('embedding', [])


def get_llm() -> LLMGateway:
    """Factory — returns the configured LLM gateway."""
    provider = getattr(settings, 'AI_PROVIDER', 'openai')
    gateways = {
        'openai': OpenAIGateway,
        'anthropic': AnthropicGateway,
        'ollama': OllamaGateway,
    }
    cls = gateways.get(provider)
    if not cls:
        raise ValueError(f"Unknown AI_PROVIDER: {provider}. Choose: {list(gateways.keys())}")
    return cls()
