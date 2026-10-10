#!/usr/bin/env python3
"""Summarize a LaTeX compiler log without flooding the agent context."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


OUTPUT_RE = re.compile(r"Output written on .+?\((\d+) pages?", re.IGNORECASE)
OVERFULL_RE = re.compile(r"Overfull \\hbox \(([0-9.]+)pt too wide\)", re.IGNORECASE)
UNDEFINED_RE = re.compile(
    r"(?:LaTeX|Package [^ ]+) Warning: (?:Reference|Citation) [`']([^`']+)[`'].*undefined",
    re.IGNORECASE,
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def compact_unique(values: list[str], limit: int = 10) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = " ".join(value.split())
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
        if len(result) >= limit:
            break
    return result


def summarize(log_path: Path, exit_code: int | None = None) -> dict[str, Any]:
    payload = log_path.read_bytes()
    text = payload.decode("utf-8", errors="replace")
    lines = text.splitlines()

    page_matches = OUTPUT_RE.findall(text)
    overfull_values = [float(value) for value in OVERFULL_RE.findall(text)]
    underfull_count = sum("Underfull \\hbox" in line for line in lines)
    fatal_lines = compact_unique([line for line in lines if line.lstrip().startswith("!")])
    undefined_keys = compact_unique(UNDEFINED_RE.findall(text), limit=20)
    undefined_summary = any(
        phrase in text
        for phrase in (
            "There were undefined references",
            "There were undefined citations",
        )
    )
    rerun_count = sum(
        any(
            phrase in line
            for phrase in (
                "Rerun to get cross-references right",
                "Label(s) may have changed",
                "Please (re)run BibTeX",
                "Please (re)run Biber",
                "Rerun to get citations correct",
            )
        )
        for line in lines
    )

    fatal_count = sum(line.lstrip().startswith("!") for line in lines)
    undefined_count = len(undefined_keys)
    if undefined_summary and undefined_count == 0:
        undefined_count = 1

    passed = (
        exit_code == 0
        and bool(page_matches)
        and fatal_count == 0
        and undefined_count == 0
        and rerun_count == 0
    )
    failed = (exit_code is not None and exit_code != 0) or fatal_count > 0 or undefined_count > 0

    return {
        "schema": "latex-log-summary/1.0",
        "status": "PASS" if passed else "FAIL" if failed else "INCOMPLETE",
        "log": {
            "path": str(log_path),
            "sha256": sha256_bytes(payload),
            "bytes": len(payload),
        },
        "compiler_exit_code": exit_code,
        "pages": int(page_matches[-1]) if page_matches else None,
        "fatal_error_count": fatal_count,
        "fatal_error_samples": fatal_lines,
        "undefined_reference_or_citation_count": undefined_count,
        "undefined_keys": undefined_keys,
        "overfull_hbox_count": len(overfull_values),
        "max_overfull_pt": max(overfull_values, default=0.0),
        "underfull_hbox_count": underfull_count,
        "rerun_warning_count": rerun_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit a compact JSON summary for a saved LaTeX compiler log"
    )
    parser.add_argument("log", help="Path to the saved .log file")
    parser.add_argument(
        "--exit-code",
        type=int,
        help="Compiler process exit code, when known",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    try:
        result = summarize(Path(args.log).expanduser().resolve(), args.exit_code)
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0 if result["status"] == "PASS" else 1
    except OSError as exc:
        print(
            json.dumps(
                {
                    "schema": "latex-log-summary/1.0",
                    "status": "ERROR",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
