#!/usr/bin/env python3
"""Reliable NotebookLM wrapper with JSON stdout for agent workflows.

The wrapper intentionally drives the public ``notebooklm`` CLI instead of
depending on private SDK internals.  It adds prompt validation, bounded retry,
per-notebook serialization, exact-question history recovery, aliases, and a
stable output envelope suitable for weaker orchestration models.

Target: notebooklm-py >= 0.8.2.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import hashlib
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


TOOL_SCHEMA = "notebooklm-agent-wrapper/2.5.2"
DEFAULT_MAX_CHARS = 3500
DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_ATTEMPTS = 2
DEFAULT_CONCURRENCY = 2
DEFAULT_ACTIVE_HISTORY_POLL = True
DEFAULT_HISTORY_POLL_INTERVAL_SECONDS = 2.5
DEFAULT_PROGRESS_HEARTBEAT_SECONDS = 10.0
DEFAULT_DIAGNOSTICS_MODE = "summary"
COMPACT_FIELD_CHARS = 1200
COMPACT_FALLBACK_CHARS = 1600
COMPACT_TOTAL_LABEL_CHARS = 6000
MAX_ERROR_CHARS = 2400
TRACE_SUFFIX_TEMPLATE = "\n\n[client-request-id:{trace_id}; ignore in answer]"
TRACE_OVERHEAD_CHARS = len(TRACE_SUFFIX_TEMPLATE.format(trace_id="0" * 32))


class InputError(ValueError):
    """Raised for deterministic caller/configuration errors."""


def configure_utf8_stdio() -> None:
    """Force stable UTF-8 JSON output on legacy Windows console encodings."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            # Embedded/test streams may not support runtime reconfiguration.
            continue


@dataclasses.dataclass(frozen=True)
class ProcessResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    elapsed_ms: int
    timed_out: bool = False


@dataclasses.dataclass(frozen=True)
class QuerySpec:
    query_id: str
    notebook_id: str
    question: str
    source_ids: tuple[str, ...]
    fresh: bool
    conversation_id: str | None
    timeout_seconds: int
    attempts: int
    max_prompt_chars: int
    active_history_poll: bool
    history_poll_interval_seconds: float
    heartbeat_seconds: float = DEFAULT_PROGRESS_HEARTBEAT_SECONDS
    diagnostics_mode: str = DEFAULT_DIAGNOSTICS_MODE


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def compact_text(value: str, limit: int = MAX_ERROR_CHARS) -> str:
    value = value.strip()
    return value if len(value) <= limit else value[: limit - 1] + "…"


_SENSITIVE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s\r\n]+"), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(?i)\b(bearer\s+)[a-zA-Z0-9_\-\.~+/]+=*"), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(?i)(cookie:\s*)[^\r\n]+"), r"\1[REDACTED_COOKIE]"),
    (re.compile(r"(?i)(set-cookie:\s*)[^\r\n]+"), r"\1[REDACTED_COOKIE]"),
    (
        re.compile(
            r"(?i)\b(__Secure-[a-zA-Z0-9_-]+|SID|HSID|SSID|APISID|SAPISID)=[^;\s\r\n]+"
        ),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(
            r"(?i)(access_token|refresh_token|master_token|oauth_token|csrf_token|"
            r"api_key|apikey|client_secret|token|password)=[\"']?([^\s&;\"'\r\n]+)[\"']?"
        ),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(
            r'(?i)(\"(?:access_token|refresh_token|master_token|oauth_token|csrf_token|'
            r'token|password|client_secret|api_key|secret)\")\s*:\s*\"[^\"]+\"'
        ),
        r'\1: "[REDACTED]"',
    ),
    (
        re.compile(
            r"(?i)('(?:access_token|refresh_token|master_token|oauth_token|csrf_token|"
            r"token|password|client_secret|api_key|secret)')\s*:\s*'[^']+'"
        ),
        r"\1: '[REDACTED]'",
    ),
    (
        re.compile(r"(?:[A-Za-z]:)?[\\/][^:\r\n]*?[\\/]\.notebooklm[\\/][a-zA-Z0-9_\-\.]+"),
        r"[REDACTED_AUTH_FILE]",
    ),
)


def sanitize_text(text: str, max_chars: int = 500) -> str:
    """Remove common credential forms before diagnostic text leaves the wrapper."""
    if not text:
        return ""
    sanitized = text
    for pattern, replacement in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    sanitized = " ".join(sanitized.split()).strip()
    return compact_text(sanitized, max_chars)


class QueryDiagnostics:
    """Collect a monotonic query timeline while exposing a compact default view."""

    def __init__(self, started_monotonic: float) -> None:
        self.started_monotonic = started_monotonic
        self.timeline: list[dict[str, Any]] = []
        self.ask_lifetimes_ms: dict[str, int] = {}
        self.history_poll_durations: list[dict[str, Any]] = []
        self.time_to_exact_history_match_ms: int | None = None
        self.retry_backoff_durations: list[dict[str, Any]] = []

    def record_event(self, event: str, **kwargs: Any) -> None:
        entry: dict[str, Any] = {
            "event": event,
            "t_ms": int((time.monotonic() - self.started_monotonic) * 1000),
        }
        entry.update(kwargs)
        self.timeline.append(entry)

    def to_dict(self, mode: str = DEFAULT_DIAGNOSTICS_MODE) -> dict[str, Any] | None:
        if mode == "off":
            return None
        poll_values = [
            int(item["duration_ms"])
            for item in self.history_poll_durations
            if isinstance(item.get("duration_ms"), int)
        ]
        backoff_values = [
            int(item["duration_ms"])
            for item in self.retry_backoff_durations
            if isinstance(item.get("duration_ms"), int)
        ]
        summary: dict[str, Any] = {
            "mode": mode,
            "total_elapsed_ms": int((time.monotonic() - self.started_monotonic) * 1000),
            "ask_lifetime_by_attempt_ms": dict(self.ask_lifetimes_ms),
            "history_polls_count": len(self.history_poll_durations),
            "history_poll_total_ms": sum(poll_values),
            "history_poll_average_ms": int(sum(poll_values) / len(poll_values)) if poll_values else None,
            "history_poll_max_ms": max(poll_values) if poll_values else None,
            "time_to_exact_history_match_ms": self.time_to_exact_history_match_ms,
            "retry_backoff_total_ms": sum(backoff_values),
            "terminal_event": self.timeline[-1]["event"] if self.timeline else None,
        }
        if mode == "full":
            summary["timeline"] = list(self.timeline)
            summary["history_poll_durations"] = list(self.history_poll_durations)
            summary["retry_backoff_durations"] = list(self.retry_backoff_durations)
        return summary


def sanitize_stderr(text: str, max_chars: int = 500) -> str:
    """Backward-compatible name for diagnostic sanitization."""
    return sanitize_text(text, max_chars=max_chars)


def json_output(payload: Mapping[str, Any], pretty: bool) -> None:
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        ),
        flush=True,
    )


def sha256_json_bytes(payload: Mapping[str, Any]) -> tuple[bytes, str]:
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    return data, hashlib.sha256(data).hexdigest()


def write_receipt(
    path_value: str,
    payload: Mapping[str, Any],
    overwrite: bool,
) -> tuple[str, str, dict[str, str] | None]:
    """Atomically save a receipt and preserve any deliberately replaced predecessor."""
    path = Path(path_value).expanduser().resolve()
    if path.exists() and not overwrite:
        raise InputError(f"Output file already exists: {path}. Use --overwrite-output deliberately.")
    path.parent.mkdir(parents=True, exist_ok=True)
    data, digest = sha256_json_bytes(payload)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    superseded: dict[str, str] | None = None
    try:
        temporary.write_bytes(data)
        if overwrite and path.exists():
            prior_bytes = path.read_bytes()
            prior_digest = hashlib.sha256(prior_bytes).hexdigest()
            archive = path.with_name(
                f"{path.name}.superseded-{utc_now().replace(':', '').replace('+', '_')}-"
                f"{prior_digest[:12]}-{uuid.uuid4().hex[:8]}"
            )
            os.replace(path, archive)
            superseded = {"path": str(archive), "sha256": prior_digest}
        if overwrite:
            os.replace(temporary, path)
        else:
            # Publish complete bytes without replacing a receipt created by another process.
            try:
                os.link(temporary, path)
            except FileExistsError as exc:
                raise InputError(f"Output file already exists: {path}. Use a new audit path.") from exc
    finally:
        with contextlib.suppress(OSError):
            temporary.unlink()
    return str(path), digest, superseded


def validate_receipt_target(args: argparse.Namespace) -> None:
    output_file = getattr(args, "output_file", None)
    if bool(getattr(args, "compact_output", False)) and not output_file:
        raise InputError("--compact-output requires --output-file so no evidence is discarded.")
    if output_file:
        path = Path(output_file).expanduser().resolve()
        if path.exists() and not bool(getattr(args, "overwrite_output", False)):
            raise InputError(
                f"Output file already exists: {path}. Use --overwrite-output deliberately."
            )


_LABEL_RE = re.compile(
    r"(?m)^[ \t]*(?:\*\*)?([A-Z][A-Z0-9_ /-]{1,48})(?::\*\*|\*\*:|:)[ \t]*(.*)$"
)
_COMPACT_LABEL_PRIORITY = (
    "VERDICT",
    "CONSISTENCY_VERDICT",
    "SNAPSHOT_MATCH",
    "IN_FORCE_CONSTRAINTS",
    "REVIEWER_REQUIREMENTS",
    "RIPPLE_TARGETS",
    "ROUTE_FINDINGS",
    "TECHNICALLY_PREFERRED_ROUTE",
    "RHETORICALLY_PREFERRED_ROUTE",
    "REQUIREMENT_COVERAGE",
    "RUBRIC_FINDINGS",
    "APPLICABLE_PAPER_RUBRIC_LAYERS",
    "OWNERSHIP_OR_SCOPE_RISKS",
    "FAILED_CRITERIA",
    "DEFECTS",
    "UNSUPPORTED_PROPOSITIONS",
    "MISSING_EVIDENCE",
    "MISSING_LOCAL_EVIDENCE",
    "EVIDENCE",
    "EXPLICIT_SOURCE_SUPPORT",
    "PRIMARY_SOURCE_MARKERS",
    "SOURCE_USE_REPORT",
    "REQUIRED_CHANGE",
    "MINIMAL_CORRECTION",
    "MINIMAL_REVISION",
    "ADDITIONAL_ROUTE",
    "REMAINING_UNCERTAINTY",
)


def extract_labeled_answer(answer: str) -> dict[str, str]:
    """Extract bounded decision fields without discarding the full saved receipt."""
    matches = list(_LABEL_RE.finditer(answer))
    found: dict[str, str] = {}
    remaining = COMPACT_TOTAL_LABEL_CHARS
    for index, match in enumerate(matches):
        label = match.group(1).strip()
        if label not in _COMPACT_LABEL_PRIORITY or label in found or remaining <= 0:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(answer)
        value = (match.group(2) + answer[match.end():end]).strip()
        bounded = compact_text(value, min(COMPACT_FIELD_CHARS, remaining))
        found[label] = bounded
        remaining -= len(bounded)
    return found


def compact_query_result(result: Mapping[str, Any]) -> dict[str, Any]:
    keep = {
        key: result[key]
        for key in (
            "query_id",
            "status",
            "notebook_id",
            "attempts",
            "elapsed_ms",
            "retrieval_method",
            "warnings",
            "intermediate_failures",
            "diagnostics",
            "error",
        )
        if key in result and result[key] not in (None, [], {})
    }
    request = result.get("request")
    if isinstance(request, Mapping):
        keep["request"] = {
            key: request[key]
            for key in (
                "question_sha256",
                "prompt_chars",
                "source_ids",
                "fresh",
                "conversation_id",
                "attempt_fresh_values",
            )
            if key in request
        }
    answer = result.get("answer")
    if isinstance(answer, str) and answer.strip():
        keep["answer_sha256"] = hashlib.sha256(answer.encode("utf-8")).hexdigest()
        keep["answer_chars"] = len(answer)
        labels = extract_labeled_answer(answer)
        label_names = [match.group(1).strip() for match in _LABEL_RE.finditer(answer)]
        duplicate_labels = sorted({label for label in label_names if label_names.count(label) > 1})
        if duplicate_labels:
            keep["answer_contract_issues"] = ["Duplicate answer labels: " + ", ".join(duplicate_labels)]
        if labels:
            keep["answer_fields"] = labels
        else:
            keep["answer_preview"] = compact_text(answer, COMPACT_FALLBACK_CHARS)
        references = result.get("references")
        keep["reference_count"] = len(references) if isinstance(references, list) else 0
    return keep


def compact_payload(
    payload: Mapping[str, Any],
    receipt_path: str,
    receipt_sha256: str,
    superseded: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    compact: dict[str, Any] = {
        key: payload[key]
        for key in ("schema", "command", "status", "created_at_utc", "elapsed_ms", "counts")
        if key in payload
    }
    compact["receipt"] = {"path": receipt_path, "sha256": receipt_sha256}
    if superseded:
        compact["receipt"]["superseded"] = dict(superseded)
    if payload.get("command") == "ask" and isinstance(payload.get("result"), Mapping):
        compact["result"] = compact_query_result(payload["result"])
    elif payload.get("command") == "batch" and isinstance(payload.get("results"), list):
        compact["results"] = [
            compact_query_result(item) for item in payload["results"] if isinstance(item, Mapping)
        ]
    return compact


def emit_result_payload(payload: Mapping[str, Any], args: argparse.Namespace) -> None:
    output_file = getattr(args, "output_file", None)
    compact = bool(getattr(args, "compact_output", False))
    if compact and not output_file:
        raise InputError("--compact-output requires --output-file so no evidence is discarded.")
    if output_file:
        path, digest, superseded = write_receipt(
            output_file,
            payload,
            bool(getattr(args, "overwrite_output", False)),
        )
        if compact:
            json_output(compact_payload(payload, path, digest, superseded), False)
            return
    json_output(payload, args.pretty)


def load_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path).expanduser().resolve()
    try:
        value = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise InputError(f"Config file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"Invalid JSON config at {config_path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InputError("The config root must be a JSON object.")
    return value


def positive_int(value: Any, field: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool):
        raise InputError(f"{field} must be an integer, not a boolean.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise InputError(f"{field} must be an integer.") from exc
    if parsed < minimum:
        raise InputError(f"{field} must be >= {minimum}.")
    return parsed


def positive_float(value: Any, field: str, *, minimum: float = 0.05) -> float:
    if isinstance(value, bool):
        raise InputError(f"{field} must be a number, not a boolean.")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise InputError(f"{field} must be a number.") from exc
    if parsed < minimum:
        raise InputError(f"{field} must be >= {minimum}.")
    return parsed


def get_setting(
    cli_value: Any,
    config: Mapping[str, Any],
    key: str,
    default: Any,
) -> Any:
    return cli_value if cli_value is not None else config.get(key, default)


def resolve_notebook(reference: str, config: Mapping[str, Any]) -> str:
    """Resolve an alias from config, otherwise treat the value as an ID."""
    notebooks = config.get("notebooks", {})
    if notebooks is not None and not isinstance(notebooks, dict):
        raise InputError("config.notebooks must be an object keyed by alias.")
    entry = notebooks.get(reference) if isinstance(notebooks, dict) else None
    if entry is None:
        if reference in {"project", "theory", "writing"}:
            raise InputError(
                f"Notebook alias {reference!r} is not configured. Run 'list' and bind it in config.notebooks."
            )
        return reference
    if isinstance(entry, str) and entry.strip():
        return entry.strip()
    if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"].strip():
        return entry["id"].strip()
    raise InputError(
        f"Notebook alias {reference!r} has no id. Run 'list', then set "
        f"config.notebooks.{reference}.id."
    )


def cli_prefix(args: argparse.Namespace, config: Mapping[str, Any]) -> list[str]:
    executable = get_setting(args.python, config, "python_executable", sys.executable)
    if not isinstance(executable, str) or not executable.strip():
        raise InputError("python_executable must be a non-empty string.")
    command = [executable, "-m", "notebooklm"]

    profile = get_setting(args.profile, config, "profile", None)
    storage = get_setting(args.storage, config, "storage", None)
    backend = get_setting(args.backend, config, "backend", None)
    if profile:
        command.extend(["--profile", str(profile)])
    if storage:
        command.extend(["--storage", str(storage)])
    if backend:
        if backend not in {"web", "android"}:
            raise InputError("backend must be 'web' or 'android'.")
        command.extend(["--backend", str(backend)])
    command.append("--quiet")
    return command


async def run_process(
    argv: Sequence[str],
    *,
    stdin_text: str | None = None,
    outer_timeout_seconds: int = 120,
) -> ProcessResult:
    start = time.monotonic()
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE if stdin_text is not None else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        return ProcessResult(
            argv=tuple(argv),
            returncode=127,
            stdout="",
            stderr=str(exc),
            elapsed_ms=int((time.monotonic() - start) * 1000),
        )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(None if stdin_text is None else stdin_text.encode("utf-8")),
            timeout=outer_timeout_seconds,
        )
        timed_out = False
    except asyncio.TimeoutError:
        process.kill()
        stdout_bytes, stderr_bytes = await process.communicate()
        timed_out = True
    except asyncio.CancelledError:
        if process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                process.kill()
        with contextlib.suppress(Exception):
            await process.communicate()
        raise

    return ProcessResult(
        argv=tuple(argv),
        returncode=124 if timed_out else int(process.returncode or 0),
        stdout=stdout_bytes.decode("utf-8", errors="replace"),
        stderr=stderr_bytes.decode("utf-8", errors="replace"),
        elapsed_ms=int((time.monotonic() - start) * 1000),
        timed_out=timed_out,
    )


def parse_json_document(text: str) -> Any:
    """Parse clean JSON or the last complete JSON document in noisy output."""
    stripped = text.strip().lstrip("\ufeff")
    if not stripped:
        raise InputError("NotebookLM returned no JSON output.")
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    candidates: list[tuple[int, Any]] = []
    for match in re.finditer(r"[\[{]", stripped):
        try:
            value, end = decoder.raw_decode(stripped[match.start() :])
        except json.JSONDecodeError:
            continue
        candidates.append((match.start() + end, value))
    if not candidates:
        raise InputError("Could not locate a complete JSON document in NotebookLM output.")
    return max(candidates, key=lambda item: item[0])[1]


def extract_payload(process: ProcessResult) -> Any | None:
    for stream in (process.stdout, process.stderr):
        try:
            return parse_json_document(stream)
        except InputError:
            continue
    return None


def extract_answer(payload: Any) -> tuple[str | None, Any]:
    if not isinstance(payload, dict):
        return None, None
    containers: list[Mapping[str, Any]] = [payload]
    for key in ("result", "data"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            containers.append(nested)
    for container in containers:
        answer = container.get("answer")
        if isinstance(answer, str) and answer.strip():
            refs = container.get("references", container.get("citations", []))
            return answer.strip(), refs
    return None, None


def normalize_question(text: str) -> str:
    return " ".join(text.split()).casefold()


def iter_history_pairs(value: Any) -> Iterable[tuple[str, str]]:
    """Yield full question/answer pairs from supported history JSON shapes."""
    if isinstance(value, dict):
        question = value.get("question")
        answer = value.get("answer")
        if isinstance(question, str) and isinstance(answer, str):
            yield question, answer
        for key in ("history", "turns", "qa_pairs", "results", "data"):
            if key in value:
                yield from iter_history_pairs(value[key])
    elif isinstance(value, list):
        if (
            len(value) == 2
            and isinstance(value[0], str)
            and isinstance(value[1], str)
        ):
            yield value[0], value[1]
        else:
            for item in value:
                yield from iter_history_pairs(item)


def classify_failure(process: ProcessResult, payload: Any | None) -> dict[str, Any]:
    rendered = " ".join(
        part for part in (process.stderr.strip(), process.stdout.strip(), json.dumps(payload, ensure_ascii=False) if payload is not None else "") if part
    )
    lowered = rendered.casefold()
    category = "upstream_error"
    retryable = False
    action = "Run the doctor command and inspect the returned NotebookLM error."

    if process.timed_out or any(token in lowered for token in ("timeout", "timed out", "readtimeout")):
        category, retryable = "timeout", True
        action = "Retry once; if it repeats, increase --timeout and run doctor."
    elif any(token in lowered for token in ("429", "rate limit", "quota", "throttl")):
        category, retryable = "rate_limit", True
        action = "Wait for the NotebookLM quota window or reduce concurrency."
    elif any(token in lowered for token in ("login", "authentication", "unauthorized", "forbidden", "cookie", "redirect")):
        category = "authentication"
        action = "Run 'python -m notebooklm auth check --test --json', then authenticate manually if needed."
    elif any(token in lowered for token in ("decode", "schema", "unexpected shape")):
        category = "schema_drift"
        action = "Check the installed notebooklm-py version and upstream compatibility."
    elif any(token in lowered for token in ("unexpected_error", "unexpected error")):
        category, retryable = "upstream_error", True
        action = (
            "Retry this exact query once without changing its prompt or source scope; "
            "if it repeats, stop and preserve the raw error."
        )
    elif process.returncode == 127:
        category = "environment"
        action = "Verify python_executable and install notebooklm-py in that environment."

    return {
        "category": category,
        "retryable": retryable,
        "message": sanitize_text(
            rendered or f"NotebookLM exited with code {process.returncode}.",
            max_chars=MAX_ERROR_CHARS,
        ),
        "suggested_action": action,
        "exit_code": process.returncode,
    }


def build_ask_command(
    prefix: Sequence[str],
    spec: QuerySpec,
) -> list[str]:
    command = list(prefix)
    command.extend(
        [
            "ask",
            "--json",
            "--request-timeout",
            str(spec.timeout_seconds),
            "--notebook",
            spec.notebook_id,
        ]
    )
    for source_id in spec.source_ids:
        command.extend(["--source", source_id])
    if spec.conversation_id:
        command.extend(["--conversation-id", spec.conversation_id])
    if spec.fresh:
        command.append("--new")
    command.extend(["--prompt-file", "-"])
    return command


async def recover_exact_history_answer(
    prefix: Sequence[str],
    spec: QuerySpec,
    expected_question: str,
) -> tuple[str, str | None] | None:
    command = list(prefix) + [
        "history",
        "--json",
        "--limit",
        "8",
        "--notebook",
        spec.notebook_id,
    ]
    history = await run_process(command, outer_timeout_seconds=min(spec.timeout_seconds, 15))
    if history.returncode != 0:
        return None
    payload = extract_payload(history)
    target = normalize_question(expected_question)
    matches = [
        (question, answer)
        for question, answer in iter_history_pairs(payload)
        if normalize_question(question) == target and answer.strip()
    ]
    if not matches:
        return None
    return matches[-1][1].strip(), None


async def probe_history_state(
    prefix: Sequence[str],
    spec: QuerySpec,
) -> str:
    """Return ``empty``, ``nonempty``, or ``unknown`` for retry decisions."""
    command = list(prefix) + [
        "history",
        "--json",
        "--limit",
        "8",
        "--notebook",
        spec.notebook_id,
    ]
    history = await run_process(command, outer_timeout_seconds=min(spec.timeout_seconds, 15))
    if history.returncode != 0:
        return "unknown"
    payload = extract_payload(history)
    if payload is None:
        return "unknown"
    return "nonempty" if list(iter_history_pairs(payload)) else "empty"


def wire_question(question: str, trace_id: str) -> str:
    """Add a unique, ignorable marker so history recovery cannot use stale data."""
    return question + TRACE_SUFFIX_TEMPLATE.format(trace_id=trace_id)


async def cancel_task(task: asyncio.Task[Any]) -> None:
    if task.done():
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


async def emit_progress_heartbeats(query_id: str, interval_seconds: float) -> None:
    """Keep an orchestrator informed while the child CLI buffers JSON output."""
    if interval_seconds <= 0:
        return
    started = time.monotonic()
    while True:
        await asyncio.sleep(interval_seconds)
        elapsed = int(time.monotonic() - started)
        print(
            f"[notebooklm-wrapper] query={query_id} state=waiting elapsed_s={elapsed}",
            file=sys.stderr,
            flush=True,
        )


async def run_ask_with_history_poll(
    prefix: Sequence[str],
    spec: QuerySpec,
    submitted_question: str,
    diagnostics: QueryDiagnostics | None = None,
    attempt: int = 1,
) -> tuple[ProcessResult | None, tuple[str, str | None] | None]:
    """Run ``ask`` while polling committed history for the same traced question."""
    ask_started = time.monotonic()
    if diagnostics:
        diagnostics.record_event("ask_process_started", attempt=attempt)

    ask_task = asyncio.create_task(
        run_process(
            build_ask_command(prefix, spec),
            stdin_text=submitted_question,
            outer_timeout_seconds=spec.timeout_seconds + 20,
        )
    )
    heartbeat_task = asyncio.create_task(
        emit_progress_heartbeats(spec.query_id, spec.heartbeat_seconds)
    )

    try:
        if not spec.active_history_poll:
            result = await ask_task
            ask_duration_ms = int((time.monotonic() - ask_started) * 1000)
            if diagnostics:
                diagnostics.ask_lifetimes_ms[str(attempt)] = ask_duration_ms
                diagnostics.record_event(
                    "ask_process_exited",
                    attempt=attempt,
                    exit_code=result.returncode,
                    wrapper_initiated=False,
                    duration_ms=ask_duration_ms,
                )
            return result, None

        done, _ = await asyncio.wait(
            {ask_task}, timeout=spec.history_poll_interval_seconds
        )
        if ask_task in done:
            result = ask_task.result()
            ask_duration_ms = int((time.monotonic() - ask_started) * 1000)
            if diagnostics:
                diagnostics.ask_lifetimes_ms[str(attempt)] = ask_duration_ms
                diagnostics.record_event(
                    "ask_process_exited",
                    attempt=attempt,
                    exit_code=result.returncode,
                    wrapper_initiated=False,
                    duration_ms=ask_duration_ms,
                )
            return result, None

        poll_index = 0
        last_poll_finished = time.monotonic()
        while True:
            poll_index += 1
            poll_started = time.monotonic()
            interval_ms = int((poll_started - last_poll_finished) * 1000)
            if diagnostics:
                diagnostics.record_event(
                    "history_poll_started",
                    attempt=attempt,
                    poll_index=poll_index,
                    interval_since_last_poll_ms=interval_ms if poll_index > 1 else None,
                )

            history_task = asyncio.create_task(
                recover_exact_history_answer(prefix, spec, submitted_question)
            )
            done, _ = await asyncio.wait(
                {ask_task, history_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if ask_task in done:
                await cancel_task(history_task)
                result = ask_task.result()
                ask_duration_ms = int((time.monotonic() - ask_started) * 1000)
                poll_duration_ms = int((time.monotonic() - poll_started) * 1000)
                if diagnostics:
                    diagnostics.history_poll_durations.append(
                        {
                            "attempt": attempt,
                            "poll_index": poll_index,
                            "duration_ms": poll_duration_ms,
                            "exact_trace_match": False,
                            "cancelled_by_ask_exit": True,
                        }
                    )
                    diagnostics.record_event(
                        "history_poll_finished",
                        attempt=attempt,
                        poll_index=poll_index,
                        duration_ms=poll_duration_ms,
                        exact_trace_match=False,
                        cancelled_by_ask_exit=True,
                    )
                    diagnostics.ask_lifetimes_ms[str(attempt)] = ask_duration_ms
                    diagnostics.record_event(
                        "ask_process_exited",
                        attempt=attempt,
                        exit_code=result.returncode,
                        wrapper_initiated=False,
                        duration_ms=ask_duration_ms,
                    )
                return result, None

            recovered = history_task.result()
            last_poll_finished = time.monotonic()
            poll_duration_ms = int((last_poll_finished - poll_started) * 1000)
            has_match = recovered is not None
            if diagnostics:
                diagnostics.history_poll_durations.append(
                    {
                        "attempt": attempt,
                        "poll_index": poll_index,
                        "duration_ms": poll_duration_ms,
                        "exact_trace_match": has_match,
                    }
                )
                diagnostics.record_event(
                    "history_poll_finished",
                    attempt=attempt,
                    poll_index=poll_index,
                    duration_ms=poll_duration_ms,
                    exact_trace_match=has_match,
                )

            if recovered:
                match_time_ms = int((time.monotonic() - diagnostics.started_monotonic) * 1000) if diagnostics else None
                if diagnostics:
                    diagnostics.time_to_exact_history_match_ms = match_time_ms
                    diagnostics.record_event(
                        "exact_trace_match_found",
                        attempt=attempt,
                        poll_index=poll_index,
                        time_to_match_ms=match_time_ms,
                    )
                await cancel_task(ask_task)
                ask_duration_ms = int((time.monotonic() - ask_started) * 1000)
                if diagnostics:
                    diagnostics.ask_lifetimes_ms[str(attempt)] = ask_duration_ms
                    diagnostics.record_event(
                        "ask_process_killed_after_history_match",
                        attempt=attempt,
                        duration_ms=ask_duration_ms,
                    )
                    diagnostics.record_event(
                        "ask_process_exited",
                        attempt=attempt,
                        exit_code=None,
                        wrapper_initiated=True,
                        duration_ms=ask_duration_ms,
                    )
                return None, recovered

            done, _ = await asyncio.wait(
                {ask_task}, timeout=spec.history_poll_interval_seconds
            )
            if ask_task in done:
                result = ask_task.result()
                ask_duration_ms = int((time.monotonic() - ask_started) * 1000)
                if diagnostics:
                    diagnostics.ask_lifetimes_ms[str(attempt)] = ask_duration_ms
                    diagnostics.record_event(
                        "ask_process_exited",
                        attempt=attempt,
                        exit_code=result.returncode,
                        wrapper_initiated=False,
                        duration_ms=ask_duration_ms,
                    )
                return result, None
    except asyncio.CancelledError:
        await cancel_task(ask_task)
        raise
    finally:
        await cancel_task(heartbeat_task)


async def execute_query(prefix: Sequence[str], spec: QuerySpec) -> dict[str, Any]:
    started = time.monotonic()
    query_diag = QueryDiagnostics(started_monotonic=started)
    query_diag.record_event(
        "query_started",
        query_id=spec.query_id,
        notebook_id=spec.notebook_id,
    )
    intermediate_failures: list[dict[str, Any]] = []
    last_error: dict[str, Any] | None = None
    attempts_made = 0
    trace_id = uuid.uuid4().hex
    submitted_question = wire_question(spec.question, trace_id)
    if len(submitted_question) > spec.max_prompt_chars:
        query_diag.record_event(
            "query_finished",
            status="error",
            category="input",
            total_elapsed_ms=int((time.monotonic() - started) * 1000),
        )
        return {
            "query_id": spec.query_id,
            "status": "error",
            "notebook_id": spec.notebook_id,
            "attempts": 0,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "intermediate_failures": intermediate_failures,
            "diagnostics": query_diag.to_dict(spec.diagnostics_mode),
            "error": {
                "category": "input",
                "retryable": False,
                "message": (
                    f"Query plus recovery marker has {len(submitted_question)} characters; "
                    f"configured maximum is {spec.max_prompt_chars}. Split the prompt or "
                    "raise the limit deliberately."
                ),
            },
        }
    request_meta = {
        "question_sha256": hashlib.sha256(spec.question.encode("utf-8")).hexdigest(),
        "prompt_chars": len(spec.question),
        "submitted_chars": len(submitted_question),
        "client_request_id": trace_id,
        "source_ids": list(spec.source_ids),
        "fresh": spec.fresh,
        "conversation_id": spec.conversation_id,
        "active_history_poll": spec.active_history_poll,
        "heartbeat_seconds": spec.heartbeat_seconds,
        "attempt_fresh_values": [],
    }
    retry_notes: list[str] = []
    attempt_spec = spec
    upstream_error_retries = 0
    for attempt in range(1, spec.attempts + 1):
        attempts_made = attempt
        if attempt > 1:
            query_diag.record_event("next_attempt_started", attempt=attempt)
        request_meta["attempt_fresh_values"].append(attempt_spec.fresh)
        process, active_recovery = await run_ask_with_history_poll(
            prefix,
            attempt_spec,
            submitted_question,
            diagnostics=query_diag,
            attempt=attempt,
        )
        if active_recovery:
            recovered_answer, _ = active_recovery
            query_diag.record_event(
                "query_finished",
                status="success",
                retrieval_method="active_history_exact_trace_match",
                total_elapsed_ms=int((time.monotonic() - started) * 1000),
            )
            return {
                "query_id": spec.query_id,
                "status": "success",
                "notebook_id": spec.notebook_id,
                "attempts": attempt,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "retrieval_method": "active_history_exact_trace_match",
                "request": request_meta,
                "answer": recovered_answer,
                "references": [],
                "warnings": retry_notes + [
                    "The server committed an answer while the direct CLI process remained open; "
                    "the local process was cancelled after an exact traced-question match."
                ],
                "intermediate_failures": intermediate_failures,
                "diagnostics": query_diag.to_dict(spec.diagnostics_mode),
            }

        if process is None:
            raise RuntimeError("ask completed without a process result or history recovery")
        payload = extract_payload(process)
        answer, references = extract_answer(payload)
        if process.returncode == 0 and answer:
            query_diag.record_event(
                "query_finished",
                status="success",
                retrieval_method="direct_cli",
                total_elapsed_ms=int((time.monotonic() - started) * 1000),
            )
            result = {
                "query_id": spec.query_id,
                "status": "success",
                "notebook_id": spec.notebook_id,
                "attempts": attempt,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "retrieval_method": "direct_cli",
                "request": request_meta,
                "answer": answer,
                "references": references if references is not None else [],
                "intermediate_failures": intermediate_failures,
                "diagnostics": query_diag.to_dict(spec.diagnostics_mode),
            }
            if retry_notes:
                result["warnings"] = retry_notes
            return result

        post_poll_start = time.monotonic()
        query_diag.record_event("history_poll_started", attempt=attempt, phase="post_exit")
        recovered = await recover_exact_history_answer(prefix, attempt_spec, submitted_question)
        post_poll_dur = int((time.monotonic() - post_poll_start) * 1000)
        has_post_match = recovered is not None
        query_diag.history_poll_durations.append(
            {
                "attempt": attempt,
                "poll_index": "post_exit",
                "duration_ms": post_poll_dur,
                "exact_trace_match": has_post_match,
            }
        )
        query_diag.record_event(
            "history_poll_finished",
            attempt=attempt,
            phase="post_exit",
            duration_ms=post_poll_dur,
            exact_trace_match=has_post_match,
        )
        if recovered:
            match_time_ms = int((time.monotonic() - started) * 1000)
            query_diag.time_to_exact_history_match_ms = match_time_ms
            query_diag.record_event(
                "exact_trace_match_found",
                attempt=attempt,
                phase="post_exit",
                time_to_match_ms=match_time_ms,
            )
            recovered_answer, _ = recovered
            query_diag.record_event(
                "query_finished",
                status="success",
                retrieval_method="history_exact_question_match",
                total_elapsed_ms=int((time.monotonic() - started) * 1000),
            )
            return {
                "query_id": spec.query_id,
                "status": "success",
                "notebook_id": spec.notebook_id,
                "attempts": attempt,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "retrieval_method": "history_exact_question_match",
                "request": request_meta,
                "answer": recovered_answer,
                "references": [],
                "warnings": retry_notes + [
                    "The direct call failed; the committed answer was recovered by exact question match."
                ],
                "intermediate_failures": intermediate_failures,
                "diagnostics": query_diag.to_dict(spec.diagnostics_mode),
            }

        last_error = classify_failure(process, payload)
        stderr_summary = sanitize_stderr(process.stderr, max_chars=500)
        query_diag.record_event(
            "failure_classified",
            attempt=attempt,
            category=last_error["category"],
            retryable=last_error["retryable"],
            exit_code=process.returncode,
            stderr_summary=stderr_summary,
        )
        intermediate_failure = {
            "attempt": attempt,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "exit_code": process.returncode,
            "category": last_error["category"],
            "retryable": last_error["retryable"],
            "stderr_summary": stderr_summary,
        }
        intermediate_failures.append(intermediate_failure)

        should_retry = bool(last_error["retryable"] and attempt < spec.attempts)
        if should_retry and last_error["category"] == "upstream_error":
            if upstream_error_retries >= 1:
                should_retry = False
            else:
                upstream_error_retries += 1

        query_diag.record_event(
            "retry_decision",
            attempt=attempt,
            retryable=last_error["retryable"],
            should_retry=should_retry,
            reason=last_error["category"],
        )

        if not should_retry:
            break

        if attempt_spec.fresh:
            history_state = await probe_history_state(prefix, attempt_spec)
            if history_state == "empty":
                attempt_spec = dataclasses.replace(attempt_spec, fresh=False)
                retry_notes.append(
                    "The fresh attempt left an empty server history; the retry preserved the "
                    "same prompt and sources without repeating the destructive reset."
                )

        backoff_seconds = min(3.0 * attempt, 6.0)
        query_diag.record_event(
            "retry_backoff_started",
            attempt=attempt,
            backoff_seconds=backoff_seconds,
        )
        backoff_start = time.monotonic()
        await asyncio.sleep(backoff_seconds)
        backoff_ms = int((time.monotonic() - backoff_start) * 1000)
        query_diag.retry_backoff_durations.append(
            {
                "attempt": attempt,
                "duration_ms": backoff_ms,
            }
        )
        query_diag.record_event(
            "retry_backoff_finished",
            attempt=attempt,
            duration_ms=backoff_ms,
        )

    total_elapsed = int((time.monotonic() - started) * 1000)
    query_diag.record_event(
        "query_finished",
        status="error",
        total_elapsed_ms=total_elapsed,
    )
    return {
        "query_id": spec.query_id,
        "status": "error",
        "notebook_id": spec.notebook_id,
        "attempts": attempts_made,
        "elapsed_ms": total_elapsed,
        "request": request_meta,
        "warnings": retry_notes,
        "intermediate_failures": intermediate_failures,
        "diagnostics": query_diag.to_dict(spec.diagnostics_mode),
        "error": last_error or {
            "category": "empty_answer",
            "retryable": False,
            "message": "NotebookLM returned no usable answer.",
            "suggested_action": "Run doctor, then retry this query only.",
        },
    }


def read_question(
    *,
    inline: Any,
    file_value: Any,
    base_dir: Path,
    allow_stdin: bool,
) -> str:
    supplied = int(inline is not None) + int(file_value is not None)
    if supplied > 1:
        raise InputError("Provide exactly one of question or question_file.")
    if inline is not None:
        if not isinstance(inline, str):
            raise InputError("question must be a string.")
        question = inline
    elif file_value is not None:
        if not isinstance(file_value, str) or not file_value.strip():
            raise InputError("question_file must be a non-empty path string.")
        path = Path(file_value).expanduser()
        if not path.is_absolute():
            path = base_dir / path
        try:
            question = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise InputError(f"Could not read question_file {path}: {exc}") from exc
    elif allow_stdin and not sys.stdin.isatty():
        question = sys.stdin.read()
    else:
        raise InputError("Provide --question, --question-file, or pipe the question through stdin.")
    if not question.strip():
        raise InputError("The question is empty.")
    return question.strip()


def validate_prompt(question: str, max_chars: int, query_id: str) -> None:
    length = len(question)
    usable_chars = max_chars - TRACE_OVERHEAD_CHARS
    if usable_chars < 1:
        raise InputError(
            f"Configured maximum {max_chars} is too small for the recovery marker."
        )
    if length > usable_chars:
        raise InputError(
            f"Query {query_id!r} has {length} characters; usable content maximum is "
            f"{usable_chars} within the configured wire limit of {max_chars}. "
            "Split the task into an atomic evidence question or raise the limit deliberately."
        )


def build_query_spec(
    raw: Mapping[str, Any],
    *,
    index: int,
    base_dir: Path,
    config: Mapping[str, Any],
    defaults: Mapping[str, Any],
) -> QuerySpec:
    query_id = raw.get("id", f"q{index:03d}")
    if not isinstance(query_id, str) or not query_id.strip():
        raise InputError(f"Query {index}: id must be a non-empty string.")

    notebook_ref = raw.get("notebook", raw.get("notebook_id"))
    if not isinstance(notebook_ref, str) or not notebook_ref.strip():
        raise InputError(f"Query {query_id!r}: notebook is required.")
    notebook_id = resolve_notebook(notebook_ref.strip(), config)

    question = read_question(
        inline=raw.get("question"),
        file_value=raw.get("question_file"),
        base_dir=base_dir,
        allow_stdin=False,
    )
    max_chars = positive_int(raw.get("max_chars", defaults["max_chars"]), "max_chars", minimum=200)
    validate_prompt(question, max_chars, query_id)

    source_ids = raw.get("source_ids", [])
    if source_ids is None:
        source_ids = []
    if not isinstance(source_ids, list) or not all(isinstance(x, str) and x.strip() for x in source_ids):
        raise InputError(f"Query {query_id!r}: source_ids must be an array of non-empty strings.")

    fresh = raw.get("fresh", defaults["fresh"])
    if not isinstance(fresh, bool):
        raise InputError(f"Query {query_id!r}: fresh must be true or false.")
    conversation_id = raw.get("conversation_id")
    if conversation_id is not None and (not isinstance(conversation_id, str) or not conversation_id.strip()):
        raise InputError(f"Query {query_id!r}: conversation_id must be a non-empty string.")
    if fresh and conversation_id:
        raise InputError(f"Query {query_id!r}: fresh and conversation_id are mutually exclusive.")

    active_history_poll = raw.get(
        "active_history_poll", defaults["active_history_poll"]
    )
    if not isinstance(active_history_poll, bool):
        raise InputError(
            f"Query {query_id!r}: active_history_poll must be true or false."
        )
    diagnostics_mode = raw.get(
        "diagnostics_mode",
        defaults.get("diagnostics_mode", DEFAULT_DIAGNOSTICS_MODE),
    )
    if diagnostics_mode not in {"off", "summary", "full"}:
        raise InputError(
            f"Query {query_id!r}: diagnostics_mode must be off, summary, or full."
        )

    return QuerySpec(
        query_id=query_id.strip(),
        notebook_id=notebook_id,
        question=question,
        source_ids=tuple(x.strip() for x in source_ids),
        fresh=fresh,
        conversation_id=conversation_id.strip() if isinstance(conversation_id, str) else None,
        timeout_seconds=positive_int(raw.get("timeout_seconds", defaults["timeout_seconds"]), "timeout_seconds", minimum=10),
        attempts=positive_int(raw.get("attempts", defaults["attempts"]), "attempts", minimum=1),
        max_prompt_chars=max_chars,
        active_history_poll=active_history_poll,
        history_poll_interval_seconds=positive_float(
            raw.get(
                "history_poll_interval_seconds",
                defaults["history_poll_interval_seconds"],
            ),
            "history_poll_interval_seconds",
        ),
        heartbeat_seconds=positive_float(
            raw.get(
                "heartbeat_seconds",
                defaults.get("heartbeat_seconds", DEFAULT_PROGRESS_HEARTBEAT_SECONDS),
            ),
            "heartbeat_seconds",
            minimum=0.0,
        ),
        diagnostics_mode=diagnostics_mode,
    )


def batch_specs(
    path: str,
    config: Mapping[str, Any],
    defaults: Mapping[str, Any],
) -> list[QuerySpec]:
    batch_path = Path(path).expanduser().resolve()
    try:
        document = json.loads(batch_path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise InputError(f"Could not read batch file {batch_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"Invalid batch JSON at {batch_path}: {exc}") from exc

    raw_queries = document.get("queries") if isinstance(document, dict) else document
    if not isinstance(raw_queries, list) or not raw_queries:
        raise InputError("Batch input must be a non-empty array or an object with a non-empty queries array.")
    specs: list[QuerySpec] = []
    for index, raw in enumerate(raw_queries, 1):
        if not isinstance(raw, dict):
            raise InputError(f"Query {index} must be a JSON object.")
        specs.append(
            build_query_spec(
                raw,
                index=index,
                base_dir=batch_path.parent,
                config=config,
                defaults=defaults,
            )
        )
    ids = [spec.query_id for spec in specs]
    duplicates = sorted({query_id for query_id in ids if ids.count(query_id) > 1})
    if duplicates:
        raise InputError(f"Duplicate query ids: {', '.join(duplicates)}")
    return specs


async def run_batch(
    prefix: Sequence[str],
    specs: Sequence[QuerySpec],
    max_concurrency: int,
) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(max_concurrency)
    notebook_locks: dict[str, asyncio.Lock] = {}

    async def guarded(spec: QuerySpec) -> dict[str, Any]:
        lock = notebook_locks.setdefault(spec.notebook_id, asyncio.Lock())
        async with semaphore:
            async with lock:
                return await execute_query(prefix, spec)

    return list(await asyncio.gather(*(guarded(spec) for spec in specs)))


async def passthrough_json(
    prefix: Sequence[str],
    command: Sequence[str],
    *,
    timeout_seconds: int = 90,
) -> tuple[dict[str, Any], int]:
    process = await run_process(list(prefix) + list(command), outer_timeout_seconds=timeout_seconds)
    payload = extract_payload(process)
    if process.returncode == 0 and payload is not None:
        return {
            "schema": TOOL_SCHEMA,
            "status": "success",
            "elapsed_ms": process.elapsed_ms,
            "result": payload,
        }, 0
    return {
        "schema": TOOL_SCHEMA,
        "status": "error",
        "elapsed_ms": process.elapsed_ms,
        "error": classify_failure(process, payload),
    }, 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Reliable NotebookLM agent wrapper (JSON on stdout)"
    )
    result.add_argument("--config", help="JSON config with aliases and defaults")
    result.add_argument("--python", help="Python executable containing notebooklm-py")
    result.add_argument("--profile", help="NotebookLM profile name")
    result.add_argument("--storage", help="NotebookLM storage path override")
    result.add_argument("--backend", choices=("web", "android"))
    result.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    sub = result.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Report package version and test authentication")
    sub.add_parser("list", help="List notebooks")

    sources = sub.add_parser("sources", help="List sources for a notebook or configured alias")
    sources.add_argument("-n", "--notebook", required=True)

    history = sub.add_parser("history", help="Read full recent server history")
    history.add_argument("-n", "--notebook", required=True)
    history.add_argument("-l", "--limit", type=int, default=5)

    ask = sub.add_parser("ask", help="Ask one validated question")
    ask.add_argument("-n", "--notebook", required=True)
    ask.add_argument(
        "--query-id",
        default="single",
        help="Stable logical ID; required for auditable route/candidate evidence",
    )
    ask.add_argument("-q", "--question")
    ask.add_argument("--question-file")
    ask.add_argument("-s", "--source", dest="source_ids", action="append", default=[])
    ask.add_argument("--fresh", action=argparse.BooleanOptionalAction, default=None,
                     help="Delete current server conversation before asking (destructive)")
    ask.add_argument("-c", "--conversation-id")
    ask.add_argument("--max-chars", type=int)
    ask.add_argument("--timeout", dest="timeout_seconds", type=int)
    ask.add_argument("--attempts", type=int)
    ask.add_argument(
        "--active-history-poll",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Poll traced server history while ask is still running",
    )
    ask.add_argument("--history-poll-interval", type=float)
    ask.add_argument(
        "--heartbeat-interval",
        dest="heartbeat_seconds",
        type=float,
        help="Emit waiting heartbeats to stderr; 0 disables them",
    )
    ask.add_argument("--diagnostics-mode", choices=("off", "summary", "full"))
    ask.add_argument("--output-file", help="Atomically save the complete JSON receipt")
    ask.add_argument(
        "--compact-output",
        action="store_true",
        help="Print a compact decision card; requires --output-file",
    )
    ask.add_argument(
        "--overwrite-output",
        action="store_true",
        help="Replace an existing file while archiving its previous bytes; never use for audit evidence",
    )

    batch = sub.add_parser("batch", help="Run validated queries concurrently across notebooks")
    batch.add_argument("-f", "--file", required=True)
    batch.add_argument("--max-chars", type=int)
    batch.add_argument("--timeout", dest="timeout_seconds", type=int)
    batch.add_argument("--attempts", type=int)
    batch.add_argument("--max-concurrency", type=int)
    batch.add_argument("--fresh", action=argparse.BooleanOptionalAction, default=None)
    batch.add_argument(
        "--active-history-poll",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    batch.add_argument("--history-poll-interval", type=float)
    batch.add_argument(
        "--heartbeat-interval",
        dest="heartbeat_seconds",
        type=float,
        help="Emit waiting heartbeats to stderr; 0 disables them",
    )
    batch.add_argument("--diagnostics-mode", choices=("off", "summary", "full"))
    batch.add_argument("--output-file", help="Atomically save the complete JSON receipt")
    batch.add_argument(
        "--compact-output",
        action="store_true",
        help="Print compact decision cards; requires --output-file",
    )
    batch.add_argument(
        "--overwrite-output",
        action="store_true",
        help="Replace an existing file while archiving its previous bytes; never use for audit evidence",
    )
    return result


async def async_main(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    prefix = cli_prefix(args, config)
    validate_receipt_target(args)

    if args.command == "doctor":
        version_process = await run_process(prefix + ["--version"], outer_timeout_seconds=20)
        version = compact_text(version_process.stdout or version_process.stderr) or None
        payload, code = await passthrough_json(
            prefix,
            ["auth", "check", "--test", "--json"],
            timeout_seconds=60,
        )
        payload["cli_version"] = version
        payload["target_minimum_version"] = "0.8.2"
        json_output(payload, args.pretty)
        return code

    if args.command == "list":
        payload, code = await passthrough_json(prefix, ["list", "--json"])
        json_output(payload, args.pretty)
        return code

    if args.command == "sources":
        notebook_id = resolve_notebook(args.notebook, config)
        payload, code = await passthrough_json(
            prefix,
            ["source", "list", "--notebook", notebook_id, "--json"],
        )
        json_output(payload, args.pretty)
        return code

    if args.command == "history":
        notebook_id = resolve_notebook(args.notebook, config)
        payload, code = await passthrough_json(
            prefix,
            ["history", "--notebook", notebook_id, "--limit", str(args.limit), "--json"],
        )
        json_output(payload, args.pretty)
        return code

    defaults = {
        "max_chars": positive_int(
            get_setting(getattr(args, "max_chars", None), config, "max_prompt_chars", DEFAULT_MAX_CHARS),
            "max_prompt_chars",
            minimum=200,
        ),
        "timeout_seconds": positive_int(
            get_setting(getattr(args, "timeout_seconds", None), config, "request_timeout_seconds", DEFAULT_TIMEOUT_SECONDS),
            "request_timeout_seconds",
            minimum=10,
        ),
        "attempts": positive_int(
            get_setting(getattr(args, "attempts", None), config, "max_attempts", DEFAULT_ATTEMPTS),
            "max_attempts",
        ),
        "fresh": get_setting(getattr(args, "fresh", None), config, "fresh_default", False),
        "active_history_poll": get_setting(
            getattr(args, "active_history_poll", None),
            config,
            "active_history_poll_default",
            DEFAULT_ACTIVE_HISTORY_POLL,
        ),
        "history_poll_interval_seconds": positive_float(
            get_setting(
                getattr(args, "history_poll_interval", None),
                config,
                "history_poll_interval_seconds",
                DEFAULT_HISTORY_POLL_INTERVAL_SECONDS,
            ),
            "history_poll_interval_seconds",
        ),
        "heartbeat_seconds": positive_float(
            get_setting(
                getattr(args, "heartbeat_seconds", None),
                config,
                "progress_heartbeat_seconds",
                DEFAULT_PROGRESS_HEARTBEAT_SECONDS,
            ),
            "progress_heartbeat_seconds",
            minimum=0.0,
        ),
        "diagnostics_mode": get_setting(
            getattr(args, "diagnostics_mode", None),
            config,
            "diagnostics_mode_default",
            DEFAULT_DIAGNOSTICS_MODE,
        ),
    }
    if not isinstance(defaults["fresh"], bool):
        raise InputError("fresh_default must be true or false.")
    if not isinstance(defaults["active_history_poll"], bool):
        raise InputError("active_history_poll_default must be true or false.")
    if defaults["diagnostics_mode"] not in {"off", "summary", "full"}:
        raise InputError("diagnostics_mode_default must be off, summary, or full.")

    if args.command == "ask":
        question = read_question(
            inline=args.question,
            file_value=args.question_file,
            base_dir=Path.cwd(),
            allow_stdin=True,
        )
        raw = {
            "id": args.query_id,
            "notebook": args.notebook,
            "question": question,
            "source_ids": args.source_ids,
            "fresh": defaults["fresh"],
            "conversation_id": args.conversation_id,
        }
        spec = build_query_spec(
            raw,
            index=1,
            base_dir=Path.cwd(),
            config=config,
            defaults=defaults,
        )
        result = await execute_query(prefix, spec)
        payload = {
            "schema": TOOL_SCHEMA,
            "command": "ask",
            "status": result["status"],
            "created_at_utc": utc_now(),
            "result": result,
        }
        emit_result_payload(payload, args)
        return 0 if result["status"] == "success" else 1

    if args.command == "batch":
        specs = batch_specs(args.file, config, defaults)
        max_concurrency = positive_int(
            get_setting(args.max_concurrency, config, "max_concurrency", DEFAULT_CONCURRENCY),
            "max_concurrency",
        )
        started = time.monotonic()
        results = await run_batch(prefix, specs, max_concurrency)
        succeeded = sum(item["status"] == "success" for item in results)
        failed = len(results) - succeeded
        status = "success" if failed == 0 else ("partial" if succeeded else "error")
        payload = {
            "schema": TOOL_SCHEMA,
            "command": "batch",
            "status": status,
            "created_at_utc": utc_now(),
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "counts": {"total": len(results), "succeeded": succeeded, "failed": failed},
            "results": results,
        }
        emit_result_payload(payload, args)
        return 0 if failed == 0 else 1

    raise InputError(f"Unsupported command: {args.command}")


def main() -> int:
    configure_utf8_stdio()
    args = parser().parse_args()
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        return 130
    except InputError as exc:
        json_output(
            {
                "schema": TOOL_SCHEMA,
                "status": "error",
                "error": {
                    "category": "input",
                    "retryable": False,
                    "message": sanitize_text(str(exc), max_chars=MAX_ERROR_CHARS),
                },
            },
            args.pretty,
        )
        return 2
    except Exception as exc:  # Fail closed with a machine-readable envelope.
        json_output(
            {
                "schema": TOOL_SCHEMA,
                "status": "error",
                "error": {
                    "category": "internal",
                    "retryable": False,
                    "message": sanitize_text(
                        f"{type(exc).__name__}: {exc}", max_chars=MAX_ERROR_CHARS
                    ),
                },
            },
            args.pretty,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
