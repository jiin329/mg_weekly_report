"""Concrete, environment-configured ``LLMClient`` for the LLM track (task 6.1).

This module provides ``HttpLLMClient`` — the real implementation of the shared
``LLMClient`` interface fixed in task 1.5. It connects to an external LLM API
whose API key and endpoint are supplied through environment variables
(``LLM_API_KEY`` / ``LLM_ENDPOINT``), satisfying Requirements 9.1 (integrate
with an LLM API) and 9.5 (configure the connection via environment variables).

Layering / boundaries:
- It REUSES, and does not redefine, the shared contract in ``app.llm``
  (``LLMClient`` / ``ReportTemplate`` / the ``LLMError`` hierarchy), the prompt
  builder in ``app.llm_prompt`` (task 6.2), and the response parser in
  ``app.llm_parsing`` (task 6.3).
- It depends on the Backend Config only in shape: it reads the same environment
  variable NAMES exported by ``app.config`` (``ENV_LLM_API_KEY`` /
  ``ENV_LLM_ENDPOINT``). It does not import BE service or FE track code.

All network I/O lives behind the small ``LLMTransport`` protocol so the request
logic can be tested without a live endpoint and swapped per provider. The
default ``UrllibTransport`` uses only the standard library (no extra runtime
dependency) and speaks an OpenAI-compatible chat-completions request.

Failure-path budget (task 6.4, Requirement 9.4): report generation may take up
to 30s on the success path (Requirement 5.3), but an unreachable/errored/slow
LLM must surface a *descriptive* error within ~5 seconds. The client therefore
caps the wait it hands to the transport at a dedicated failure budget
(``DEFAULT_FAILURE_TIMEOUT_SECONDS`` = 5s, configurable): the effective transport
timeout is ``min(request_timeout, failure_budget)``, so a slow or dead endpoint
raises inside the 5s budget. The transport normalises its failures
(``TimeoutError`` for timeouts, ``ConnectionError`` for everything else) and the
client maps those onto the shared contract: timeouts -> ``LLMTimeoutError``
(``LLM_TIMEOUT``), all other transport/parse failures -> ``LLMUnavailableError``
(``LLM_UNAVAILABLE``). Each raised error carries the underlying cause so the
message is descriptive.
"""

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Optional, Protocol, runtime_checkable

from app.config import ENV_LLM_API_KEY, ENV_LLM_ENDPOINT
from app.error_codes import ErrorCode
from app.llm import (
    DEFAULT_REPORT_TEMPLATE,
    LLMError,
    LLMTimeoutError,
    LLMUnavailableError,
    ReportTemplate,
)
from app.llm_parsing import parse_report_response
from app.llm_prompt import build_prompt
from app.models import Message, WeeklyReport

# Default request timeout (seconds). Report generation is allowed up to 30s
# end-to-end on the success path (Requirement 5.3).
_DEFAULT_TIMEOUT_SECONDS = 30.0

# Failure-path budget (seconds). An unreachable/errored/slow LLM must surface a
# descriptive error within ~5 seconds (Requirement 9.4). The client caps the
# wait handed to the transport at this budget so a dead endpoint fails fast,
# independent of the (larger) success-path request timeout. Exported so callers
# and tests can reference the contract value.
DEFAULT_FAILURE_TIMEOUT_SECONDS = 5.0

# Default model name for the OpenAI-compatible request. Overridable via the
# constructor so a different provider/model can be selected without code change.
_DEFAULT_MODEL = "gpt-4o-mini"


class LLMConfigError(LLMError):
    """Required LLM configuration (API key/endpoint) is missing or empty.

    Raised while constructing the client so a misconfigured environment fails
    fast and names each missing variable (Requirements 9.5, 10.6, 11.9). Carries
    ``ErrorCode.CONFIG_MISSING`` so a caller can translate it into a structured
    error response.
    """

    code = ErrorCode.CONFIG_MISSING

    def __init__(self, missing: list[str]) -> None:
        self.missing = list(missing)
        super().__init__(
            "missing required LLM configuration: " + ", ".join(self.missing),
            details={"missing": self.missing},
        )


@runtime_checkable
class LLMTransport(Protocol):
    """Sends a prompt to the LLM endpoint and returns the raw response text.

    Isolating network I/O behind this protocol lets the client be tested without
    a live endpoint and lets a different provider be plugged in without touching
    the client's prompt/parse wiring. Implementations SHOULD raise
    ``TimeoutError`` on timeout and any other exception on transport failure;
    the client maps those onto the shared ``LLMError`` hierarchy.
    """

    def send(
        self, *, endpoint: str, api_key: str, prompt: str, timeout: float
    ) -> str:
        ...


class UrllibTransport:
    """Standard-library transport speaking an OpenAI-compatible chat request.

    Uses ``urllib`` so it adds no runtime dependency. It POSTs the prompt as a
    single user message and returns the assistant message content (which the
    parser then turns into a ``WeeklyReport``). If the provider does not wrap the
    content in the OpenAI ``choices`` shape, the whole decoded body is returned
    and left to the parser's best-effort JSON extraction.
    """

    def __init__(self, model: str = _DEFAULT_MODEL) -> None:
        self._model = model

    def send(
        self, *, endpoint: str, api_key: str, prompt: str, timeout: float
    ) -> str:
        payload = json.dumps(
            {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self._chat_completions_url(endpoint),
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except (socket.timeout, TimeoutError) as exc:
            raise TimeoutError(str(exc)) from exc
        except urllib.error.URLError as exc:
            # A URLError can wrap a timeout; surface it as a timeout so the client
            # maps it to LLM_TIMEOUT rather than LLM_UNAVAILABLE.
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise TimeoutError(str(exc)) from exc
            raise ConnectionError(str(exc)) from exc
        return self._extract_content(body)

    @staticmethod
    def _chat_completions_url(endpoint: str) -> str:
        base = endpoint.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    @staticmethod
    def _extract_content(body: str) -> str:
        try:
            decoded = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            return body
        if isinstance(decoded, dict):
            choices = decoded.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                message = first.get("message") if isinstance(first, dict) else None
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message["content"]
        return body


class HttpLLMClient:
    """Environment-configured ``LLMClient`` that calls an external LLM API.

    Conforms to the task 1.5 ``LLMClient`` interface: ``generate`` takes the
    room's messages plus a ``ReportTemplate`` and returns a parsed
    ``WeeklyReport``.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        failure_timeout_seconds: float = DEFAULT_FAILURE_TIMEOUT_SECONDS,
        model: str = _DEFAULT_MODEL,
        transport: Optional[LLMTransport] = None,
    ) -> None:
        """Resolve credentials from the environment (or explicit overrides).

        Args:
            api_key: Explicit API key; falls back to ``LLM_API_KEY`` when None.
            endpoint: Explicit endpoint; falls back to ``LLM_ENDPOINT`` when None.
            timeout_seconds: Success-path per-request timeout (Requirement 5.3).
            failure_timeout_seconds: Failure-path budget (Requirement 9.4). The
                effective timeout handed to the transport is
                ``min(timeout_seconds, failure_timeout_seconds)`` so an
                unreachable/slow endpoint fails within this budget. Defaults to
                ``DEFAULT_FAILURE_TIMEOUT_SECONDS`` (5s).
            model: Model name for the default transport.
            transport: Transport used to reach the endpoint. Defaults to the
                standard-library ``UrllibTransport``; tests inject a fake.

        Raises:
            LLMConfigError: If the resolved API key or endpoint is missing/blank.
        """
        resolved_key = (
            api_key if api_key is not None else os.environ.get(ENV_LLM_API_KEY, "")
        )
        resolved_endpoint = (
            endpoint if endpoint is not None else os.environ.get(ENV_LLM_ENDPOINT, "")
        )

        missing: list[str] = []
        if not resolved_key or not resolved_key.strip():
            missing.append(ENV_LLM_API_KEY)
        if not resolved_endpoint or not resolved_endpoint.strip():
            missing.append(ENV_LLM_ENDPOINT)
        if missing:
            raise LLMConfigError(missing)

        self._api_key = resolved_key.strip()
        self._endpoint = resolved_endpoint.strip()
        # Cap the wait at the failure budget so a dead/slow endpoint surfaces an
        # error within ~5s (Req 9.4), without ever inflating a smaller request
        # timeout a caller explicitly asked for.
        self._timeout = min(timeout_seconds, failure_timeout_seconds)
        self._failure_timeout = failure_timeout_seconds
        self._transport: LLMTransport = transport or UrllibTransport(model)

    def generate(
        self,
        messages: list[Message],
        template: ReportTemplate = DEFAULT_REPORT_TEMPLATE,
    ) -> WeeklyReport:
        """Turn a room's messages into a ``WeeklyReport`` via the LLM API.

        Composes the prompt (task 6.2), sends it through the transport within
        the failure budget, and parses the raw response (task 6.3). Failures are
        mapped onto the shared contract within ~5s (Requirement 9.4):

        - a timeout (socket timeout, urllib timeout-wrapped ``URLError``, or
          exceeding the failure budget) surfaces as ``LLMTimeoutError``
          (``LLM_TIMEOUT``);
        - any other transport failure (connection refused, DNS failure, HTTP
          error, or a malformed/unexpected response) surfaces as
          ``LLMUnavailableError`` (``LLM_UNAVAILABLE``).

        Each error carries the underlying cause in ``details`` so the message is
        descriptive. On failure the caller (ReportService) keeps the room Active
        with no partial state (Requirement 5.7).
        """
        prompt = build_prompt(messages, template)
        try:
            raw = self._transport.send(
                endpoint=self._endpoint,
                api_key=self._api_key,
                prompt=prompt,
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            # Timeouts (incl. exceeding the failure budget) -> LLM_TIMEOUT.
            raise LLMTimeoutError(
                "LLM request timed out",
                details={
                    "cause": str(exc),
                    "timeoutSeconds": self._timeout,
                    "failureBudgetSeconds": self._failure_timeout,
                },
            ) from exc
        except LLMError:
            # Already a structured LLM error (e.g. from a custom transport).
            raise
        except Exception as exc:  # noqa: BLE001 - map any transport failure to the contract
            # Connection refused / DNS / HTTP error / other -> LLM_UNAVAILABLE.
            raise LLMUnavailableError(
                "LLM API is unavailable or returned an error",
                details={"cause": str(exc), "causeType": type(exc).__name__},
            ) from exc

        return parse_report_response(raw, template)
