"""Parsing of raw LLM responses into a structured ``WeeklyReport`` (task 6.3).

This module implements Requirement 9.3 ("parse the response into the
Weekly_Report format") on top of the shared contract fixed in task 1.5:

- ``app.models.WeeklyReport`` — the target model. Every one of its four sections
  (``writtenDate``, ``achievements``, ``nextWeekPlan``, ``issues``) is required,
  so constructing one already guarantees "all four sections present"
  (Requirement 5.2).
- ``app.llm.LLMUnavailableError`` — the error a caller (ReportService, task 4.7)
  translates into a structured ``LLM_UNAVAILABLE`` response. We raise it whenever
  the raw response cannot be turned into a complete report.

Design decisions for malformed / incomplete responses:

- Because the four sections are MANDATORY, we never invent a silent default for a
  missing or blank section. Instead we raise ``LLMUnavailableError``: from the
  caller's point of view the LLM produced an unusable answer, which maps cleanly
  to the existing ``LLM_UNAVAILABLE`` error code.
- We accept either an already-decoded ``dict`` or a ``str``. For a string we try
  ``json.loads`` directly and, failing that, extract the first JSON object found
  in the text (LLMs commonly wrap JSON in prose or a ```json fenced block).

The function is pure and deterministic: no network, no environment access, no
clock — the same input always yields the same result.
"""

import json
import re
from typing import Union

from app.llm import DEFAULT_REPORT_TEMPLATE, LLMUnavailableError, ReportTemplate
from app.models import WeeklyReport

# Matches the first balanced-looking JSON object in a larger string. This is a
# best-effort extraction for responses that wrap JSON in prose or a markdown
# code fence; the extracted candidate is still validated by json.loads.
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_report_response(
    raw: Union[str, dict],
    template: ReportTemplate = DEFAULT_REPORT_TEMPLATE,
) -> WeeklyReport:
    """Parse a raw LLM response into a validated ``WeeklyReport``.

    Args:
        raw: The LLM output, either an already-decoded ``dict`` or a JSON string
            (optionally embedded in surrounding prose / a markdown code fence).
        template: The report template describing the required sections. Defaults
            to the shared ``DEFAULT_REPORT_TEMPLATE``; used to know which section
            keys must be present.

    Returns:
        A ``WeeklyReport`` with all four sections populated.

    Raises:
        LLMUnavailableError: If the response is not a JSON object, is missing any
            required section, or leaves any section blank. Such a response is an
            unusable LLM output, mapped to ``ErrorCode.LLM_UNAVAILABLE``.
    """
    data = _to_mapping(raw)
    sections = _extract_sections(data, template.sections)
    # Every field is required on WeeklyReport, so this construction is the final
    # guarantee that all four sections are present (Requirement 5.2 / 9.3).
    return WeeklyReport(**sections)


def _to_mapping(raw: Union[str, dict]) -> dict:
    """Coerce a raw response into a JSON object (dict), else raise.

    Accepts a dict as-is, or parses a string as JSON (with a fallback that pulls
    the first ``{...}`` object out of surrounding text).
    """
    if isinstance(raw, dict):
        return raw

    if isinstance(raw, str):
        parsed = _loads_json_object(raw)
        if parsed is not None:
            return parsed
        raise LLMUnavailableError(
            "LLM response is not valid JSON containing a report object",
            details={"raw": raw},
        )

    raise LLMUnavailableError(
        f"unsupported LLM response type: {type(raw).__name__}",
    )


def _loads_json_object(text: str):
    """Return the JSON object encoded in ``text``, or ``None`` if there isn't one.

    Tries a direct decode first, then falls back to extracting the first
    ``{...}`` span (handles JSON wrapped in prose or a ```json fence).
    """
    for candidate in _json_candidates(text):
        try:
            value = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _json_candidates(text: str):
    """Yield candidate JSON strings to attempt decoding, in priority order."""
    stripped = text.strip()
    yield stripped
    match = _JSON_OBJECT_RE.search(text)
    if match is not None:
        yield match.group(0)


def _extract_sections(data: dict, section_keys: tuple[str, ...]) -> dict:
    """Pull every required section out of ``data`` as a non-blank string.

    Raises ``LLMUnavailableError`` if a section is missing or blank so that no
    silent default is ever substituted for real LLM content.
    """
    sections: dict[str, str] = {}
    for key in section_keys:
        if key not in data:
            raise LLMUnavailableError(
                f"LLM response is missing required section: {key}",
                details={"missing": key},
            )
        value = data[key]
        if not isinstance(value, str) or not value.strip():
            raise LLMUnavailableError(
                f"LLM response has an empty section: {key}",
                details={"empty": key},
            )
        sections[key] = value
    return sections
