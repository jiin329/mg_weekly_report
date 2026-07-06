"""AWS Bedrock ``LLMClient`` — provider option B (task 6.1 / integration 8.1).

This module provides ``BedrockLLMClient``, a concrete implementation of the
shared ``LLMClient`` interface (task 1.5) that reaches an Anthropic/Amazon model
hosted on **Amazon Bedrock** via the ``bedrock-runtime`` ``converse`` API.

Why a separate client (vs. the OpenAI-compatible ``HttpLLMClient``):
- Bedrock does not authenticate with a single ``Authorization: Bearer <key>``
  header against a ``/chat/completions`` URL. It uses AWS credentials (SigV4 via
  the standard boto3 credential chain — env keys, a shared profile, or a Bedrock
  API key exported as ``AWS_BEARER_TOKEN_BEDROCK``) plus a region and a model id.
- The request/response payloads differ from the OpenAI schema.

Layering / boundaries:
- REUSES the shared contract in ``app.llm`` (``LLMClient`` / ``ReportTemplate`` /
  the ``LLMError`` hierarchy), the prompt builder (``app.llm_prompt``), the parser
  (``app.llm_parsing``), and the shared generate flow
  (``app.llm_client.generate_report_via_prompt``) so the error taxonomy and
  timeout budget are identical across providers.
- boto3 is imported lazily inside the invoker so environments using provider A
  (OpenAI) do not need it installed. Install it only for the Bedrock provider
  (``pip install boto3``).

Failure-path budget (Requirement 9.4): identical to the HTTP client — an
unreachable/slow endpoint must surface a descriptive error within ~5s. The
botocore client is configured with the failure budget as its read/connect
timeout and retries disabled, and botocore timeouts are normalised to
``TimeoutError`` so the shared flow maps them to ``LLMTimeoutError``
(``LLM_TIMEOUT``); every other failure maps to ``LLMUnavailableError``
(``LLM_UNAVAILABLE``).
"""

import json
import os
from typing import Optional, Protocol, runtime_checkable

from app.config import (
    ENV_AWS_DEFAULT_REGION,
    ENV_AWS_REGION,
    ENV_BEDROCK_MODEL_ID,
)
from app.llm import (
    DEFAULT_REPORT_TEMPLATE,
    LLMUnavailableError,
    ReportTemplate,
)
from app.llm_client import (
    DEFAULT_FAILURE_TIMEOUT_SECONDS,
    LLMConfigError,
    generate_report_via_prompt,
)
from app.models import Message, WeeklyReport

# Success-path per-request timeout (Requirement 5.3). Kept in sync with the HTTP
# client's default so both providers behave identically.
_DEFAULT_TIMEOUT_SECONDS = 30.0

# Default max output tokens for the report. Overridable via the constructor.
_DEFAULT_MAX_TOKENS = 2000

# botocore exception class names that represent a timeout (matched by name to
# avoid importing botocore at module import time).
_TIMEOUT_EXC_NAMES = frozenset(
    {"ReadTimeoutError", "ConnectTimeoutError", "ConnectionClosedError"}
)


@runtime_checkable
class BedrockInvoker(Protocol):
    """Sends a prompt to Bedrock and returns the raw assistant text.

    Isolating the AWS call behind this protocol lets ``BedrockLLMClient`` be
    tested without boto3 or a live account (tests inject a fake). Implementations
    SHOULD raise ``TimeoutError`` on timeout and any other exception on failure;
    the shared generate flow maps those onto the ``LLMError`` hierarchy.
    """

    def invoke(self, prompt: str, timeout: float) -> str:
        ...


class Boto3BedrockInvoker:
    """Default ``BedrockInvoker`` using boto3's ``bedrock-runtime`` converse API.

    boto3/botocore are imported lazily on first use so provider A (OpenAI) users
    need not install them. The botocore client is built once with the failure
    budget as its read/connect timeout and retries disabled, so a dead/slow
    endpoint fails within ~5s (Requirement 9.4).
    """

    def __init__(
        self,
        *,
        model_id: str,
        region: Optional[str],
        max_tokens: int,
        timeout: float,
    ) -> None:
        self._model_id = model_id
        self._region = region
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._client = None  # built lazily

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:  # pragma: no cover - depends on env
            raise LLMUnavailableError(
                "boto3 is required for the Bedrock provider; "
                "install it with 'pip install boto3'",
                details={"cause": str(exc)},
            ) from exc

        config = Config(
            read_timeout=self._timeout,
            connect_timeout=self._timeout,
            retries={"max_attempts": 0},
        )
        kwargs: dict = {"config": config}
        if self._region:
            kwargs["region_name"] = self._region
        self._client = boto3.client("bedrock-runtime", **kwargs)
        return self._client

    def invoke(self, prompt: str, timeout: float) -> str:
        client = self._get_client()
        try:
            response = client.converse(
                modelId=self._model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": self._max_tokens},
            )
        except Exception as exc:  # noqa: BLE001 - normalise botocore failures
            if type(exc).__name__ in _TIMEOUT_EXC_NAMES:
                # Let the shared flow map this to LLM_TIMEOUT.
                raise TimeoutError(str(exc)) from exc
            raise
        return _extract_text(response)


def _extract_text(response: dict) -> str:
    """Pull the assistant text out of a Bedrock ``converse`` response.

    Falls back to a JSON dump of the whole response so the parser's best-effort
    JSON extraction can still run if the shape is unexpected.
    """
    try:
        content = response["output"]["message"]["content"]
    except (KeyError, TypeError):
        return json.dumps(response, default=str)
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                return block["text"]
    return json.dumps(response, default=str)


class BedrockLLMClient:
    """Environment-configured ``LLMClient`` that calls Amazon Bedrock.

    Conforms to the task 1.5 ``LLMClient`` interface: ``generate`` takes the
    room's messages plus a ``ReportTemplate`` and returns a parsed
    ``WeeklyReport``.

    Configuration (option B):
    - ``BEDROCK_MODEL_ID`` (required): the model id or inference-profile ARN.
    - ``AWS_REGION`` / ``AWS_DEFAULT_REGION`` (optional here; boto3 may also read
      it from the shared AWS config): the region for the bedrock-runtime client.
    - AWS credentials: resolved by boto3's standard chain (env keys, profile, or
      a Bedrock API key via ``AWS_BEARER_TOKEN_BEDROCK``).
    """

    def __init__(
        self,
        *,
        model_id: Optional[str] = None,
        region: Optional[str] = None,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        failure_timeout_seconds: float = DEFAULT_FAILURE_TIMEOUT_SECONDS,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        invoker: Optional[BedrockInvoker] = None,
    ) -> None:
        """Resolve Bedrock config from the environment (or explicit overrides).

        Raises:
            LLMConfigError: If the model id is missing/blank (names
                ``BEDROCK_MODEL_ID``), so a misconfigured Bedrock environment
                fails fast (Requirements 9.5, 11.9) carrying ``CONFIG_MISSING``.
        """
        resolved_model = (
            model_id
            if model_id is not None
            else os.environ.get(ENV_BEDROCK_MODEL_ID, "")
        )
        if not resolved_model or not resolved_model.strip():
            raise LLMConfigError([ENV_BEDROCK_MODEL_ID])

        resolved_region = region
        if resolved_region is None:
            resolved_region = (
                os.environ.get(ENV_AWS_REGION, "").strip()
                or os.environ.get(ENV_AWS_DEFAULT_REGION, "").strip()
                or None
            )

        self._model_id = resolved_model.strip()
        self._region = resolved_region
        # Cap the wait at the failure budget so a dead/slow endpoint surfaces an
        # error within ~5s (Req 9.4), never inflating a smaller request timeout.
        self._timeout = min(timeout_seconds, failure_timeout_seconds)
        self._failure_timeout = failure_timeout_seconds
        self._invoker: BedrockInvoker = invoker or Boto3BedrockInvoker(
            model_id=self._model_id,
            region=self._region,
            max_tokens=max_tokens,
            timeout=self._timeout,
        )

    def generate(
        self,
        messages: list[Message],
        template: ReportTemplate = DEFAULT_REPORT_TEMPLATE,
    ) -> WeeklyReport:
        """Turn a room's messages into a ``WeeklyReport`` via Bedrock.

        Uses the shared generate flow so prompt composition, response parsing,
        and the error taxonomy (timeouts -> ``LLM_TIMEOUT``, everything else ->
        ``LLM_UNAVAILABLE``) are identical to the OpenAI-compatible client.
        """
        return generate_report_via_prompt(
            lambda prompt, timeout: self._invoker.invoke(prompt, timeout),
            messages,
            template,
            timeout=self._timeout,
            failure_timeout=self._failure_timeout,
        )
