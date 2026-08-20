from __future__ import annotations

"""OpenRouter wiring for the OpenAI Agents SDK + Temporal plugin.

Pinned path (lab v1):
- Chat Completions only (not Responses API)
- AsyncOpenAI(base_url=OpenRouter)
- OpenAIProvider(use_responses=False) handed to OpenAIAgentsPlugin
- No LiteLLM / Any-LLM
- Tracing disabled (no OpenAI platform key required)
"""

from agents import OpenAIProvider, set_tracing_disabled
from openai import AsyncOpenAI

from agents_lab.config import Settings

_client: AsyncOpenAI | None = None
_provider: OpenAIProvider | None = None


def configure_openrouter(settings: Settings) -> tuple[AsyncOpenAI, OpenAIProvider]:
    """Build the OpenRouter client and Chat Completions provider used by the worker."""
    global _client, _provider

    client = AsyncOpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
        max_retries=0,
        default_headers={
            "HTTP-Referer": "https://github.com/Abhi-Gautam/agents",
            "X-OpenRouter-Title": "agents-lab",
        },
    )
    # Temporal's ModelActivity uses this provider; use_responses=False forces Chat Completions.
    provider = OpenAIProvider(
        openai_client=client,
        use_responses=False,
        use_responses_websocket=False,
    )
    set_tracing_disabled(disabled=True)
    _client = client
    _provider = provider
    return client, provider


def get_model_provider() -> OpenAIProvider:
    if _provider is None:
        raise RuntimeError("configure_openrouter() must run before starting the worker")
    return _provider
