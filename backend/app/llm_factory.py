"""LLM client factory — selects provider A/B from configuration.

``build_llm_client`` reads ``LLM_PROVIDER`` (via ``app.config.resolve_provider``)
and returns the matching concrete ``LLMClient`` (task 1.5 interface):

- ``openai``  (option A, default): ``HttpLLMClient`` speaking an OpenAI-compatible
  ``/chat/completions`` request, authenticated with ``LLM_API_KEY`` against
  ``LLM_ENDPOINT``. An optional ``LLM_MODEL`` overrides the model name.
- ``bedrock`` (option B): ``BedrockLLMClient`` calling Amazon Bedrock's
  ``converse`` API, configured with ``BEDROCK_MODEL_ID`` and an AWS region, with
  credentials resolved by boto3's standard chain.

This is the single seam the integration step (task 8.1) uses to swap the BE
track's ``StubLLMClient`` for a real, environment-selected client — without the
callers (ReportService) knowing which provider is active. Selecting a provider
is purely a ``.env`` change; no code change is required to move between A and B.
"""

import os
from typing import Callable, Optional

from app.config import (
    ENV_LLM_MODEL,
    PROVIDER_BEDROCK,
    PROVIDER_OPENAI,
    resolve_provider,
)
from app.error_codes import ErrorCode
from app.llm import DEFAULT_REPORT_TEMPLATE, LLMClient, LLMError, ReportTemplate
from app.llm_bedrock import BedrockLLMClient
from app.llm_client import HttpLLMClient, UrllibTransport
from app.models import Message, WeeklyReport


class UnsupportedProviderError(LLMError):
    """``LLM_PROVIDER`` is set to an unknown value.

    Carries ``ErrorCode.CONFIG_MISSING`` so a caller can render it as a
    structured configuration error identifying the offending value and the
    supported providers.
    """

    code = ErrorCode.CONFIG_MISSING

    def __init__(self, provider: str) -> None:
        self.provider = provider
        supported = ", ".join((PROVIDER_OPENAI, PROVIDER_BEDROCK))
        super().__init__(
            f"unsupported LLM_PROVIDER '{provider}'; supported: {supported}",
            details={
                "provider": provider,
                "supported": [PROVIDER_OPENAI, PROVIDER_BEDROCK],
            },
        )


def build_llm_client(provider: Optional[str] = None) -> LLMClient:
    """Build the configured ``LLMClient``.

    Args:
        provider: Explicit provider override; defaults to ``resolve_provider()``
            (the ``LLM_PROVIDER`` env var, or ``openai`` when unset).

    Returns:
        A concrete ``LLMClient`` for the selected provider.

    Raises:
        LLMConfigError: If the selected provider's required configuration is
            missing (e.g. ``LLM_API_KEY``/``LLM_ENDPOINT`` for OpenAI, or
            ``BEDROCK_MODEL_ID`` for Bedrock).
        UnsupportedProviderError: If ``LLM_PROVIDER`` is an unknown value.
    """
    selected = (provider or resolve_provider()).strip().lower()

    if selected == PROVIDER_OPENAI:
        model = os.environ.get(ENV_LLM_MODEL, "").strip()
        if model:
            return HttpLLMClient(transport=UrllibTransport(model))
        return HttpLLMClient()

    if selected == PROVIDER_BEDROCK:
        return BedrockLLMClient()

    raise UnsupportedProviderError(selected)


class LazyLLMClient:
    """An ``LLMClient`` that defers building the real provider until first use.

    Integration wiring (task 8.1) replaces the BE track's ``StubLLMClient`` with
    the real, ``.env``-selected client. Building that client eagerly would
    require valid provider configuration the moment a ``ReportService`` is
    constructed — even for requests that never reach the LLM (e.g. an invalid
    room id returning ``ROOM_NOT_FOUND``). This wrapper resolves the provider via
    ``build_llm_client()`` only on the first ``generate`` call and caches it, so:

    - report generation uses the real provider chosen by ``LLM_PROVIDER``;
    - a misconfigured environment surfaces as an ``LLMError`` (``CONFIG_MISSING``
      / ``UnsupportedProviderError``) at generation time, which ``ReportService``
      already maps to a structured error response;
    - non-LLM request paths never trigger provider construction.

    Conforms to the shared ``LLMClient`` interface (task 1.5).
    """

    def __init__(self, factory: Callable[[], LLMClient] = build_llm_client) -> None:
        self._factory = factory
        self._client: Optional[LLMClient] = None

    def generate(
        self,
        messages: list[Message],
        template: ReportTemplate = DEFAULT_REPORT_TEMPLATE,
    ) -> WeeklyReport:
        if self._client is None:
            self._client = self._factory()
        return self._client.generate(messages, template)
