#!/usr/bin/env python3
"""Validate an evidence-controlled academic reviewer ledger.

Stdlib-only so it can run from the same supported Python environments.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


STATUSES = {
    "OPEN",
    "PARTIAL",
    "RESOLVED",
    "OBSOLETE_SCOPE",
    "NEEDS_DECISION",
    "BLOCKED",
}
SEVERITIES = {"BLOCKER", "MAJOR", "MINOR", "EDITORIAL"}
WORK_TYPES = {"PROSE_FIX", "EVIDENCE_NEEDED", "AUTHOR_DECISION"}
RUBRIC_OUTCOMES = {"PASS", "PARTIAL", "FAIL", "NOT_APPLICABLE", "UNVERIFIABLE"}
ROUTE_SELECTION_STATES = {
    "AWAITING_USER_APPROVAL",
    "SELECTED",
    "NEEDS_HUMAN_DECISION",
    "BLOCKED",
    "SKIPPED",
}


def expand_expected(specification: str) -> list[str]:
    result: list[str] = []
    for token in (piece.strip() for piece in specification.split(",")):
        if not token:
            continue
        match = re.fullmatch(r"([A-Za-z]+)(\d+)-([A-Za-z]+)?(\d+)", token)
        if match:
            prefix, start_raw, end_prefix, end_raw = match.groups()
            if end_prefix and end_prefix.casefold() != prefix.casefold():
                raise ValueError(f"Mismatched range prefixes in {token!r}.")
            start, end = int(start_raw), int(end_raw)
            if end < start:
                raise ValueError(f"Descending range is not allowed: {token!r}.")
            result.extend(f"{prefix.upper()}{number}" for number in range(start, end + 1))
        elif re.fullmatch(r"[A-Za-z]+\d+", token):
            result.append(token.upper())
        else:
            raise ValueError(f"Invalid expected-ID token: {token!r}.")
    if len(set(result)) != len(result):
        raise ValueError("Expected-ID specification contains duplicates.")
    return result


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


def validate_evidence(comment_id: str, evidence: Any, errors: list[str]) -> None:
    if not isinstance(evidence, list):
        errors.append(f"{comment_id}: evidence must be an array.")
        return
    for index, item in enumerate(evidence, 1):
        prefix = f"{comment_id}.evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: must be an object.")
            continue
        if not is_nonempty_string(item.get("file")):
            errors.append(f"{prefix}: file is required.")
        if not is_nonempty_string(item.get("anchor")):
            errors.append(f"{prefix}: stable anchor is required; a line alone is insufficient.")
        if not is_nonempty_string(item.get("observation")):
            errors.append(f"{prefix}: observation is required.")
        line = item.get("line")
        if line is not None and (isinstance(line, bool) or not isinstance(line, int) or line < 1):
            errors.append(f"{prefix}: line must be a positive integer when present.")


def validate_rubric_findings(
    comment_id: str,
    findings: Any,
    errors: list[str],
) -> list[str]:
    if findings is None:
        return []
    if not isinstance(findings, list):
        errors.append(f"{comment_id}: rubric_findings must be an array when present.")
        return []
    outcomes: list[str] = []
    for index, finding in enumerate(findings, 1):
        prefix = f"{comment_id}.rubric_findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{prefix}: must be an object.")
            continue
        criterion_id = finding.get("criterion_id")
        if not is_nonempty_string(criterion_id) or not re.fullmatch(
            r"L(?:10|[0-9])(?:[.][A-Za-z0-9_-]+)?",
            criterion_id.strip(),
        ):
            errors.append(f"{prefix}: criterion_id must look like L5 or L4.ML.")
        outcome = finding.get("outcome")
        if outcome not in RUBRIC_OUTCOMES:
            errors.append(f"{prefix}: outcome must be one of {sorted(RUBRIC_OUTCOMES)}.")
        else:
            outcomes.append(outcome)
        if not is_nonempty_string(finding.get("observation")):
            errors.append(f"{prefix}: observation is required.")
    return outcomes


def validate_route_decision_link(comment_id: str, value: Any, errors: list[str]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        errors.append(f"{comment_id}: route_decision must be an object when present.")
        return None
    if not is_nonempty_string(value.get("file")):
        errors.append(f"{comment_id}.route_decision: file is required.")
    selection_state = value.get("selection_state")
    if selection_state not in ROUTE_SELECTION_STATES:
        errors.append(
            f"{comment_id}.route_decision: selection_state must be one of "
            f"{sorted(ROUTE_SELECTION_STATES)}."
        )
        return None
    selected_route_id = value.get("selected_route_id")
    if selection_state == "SELECTED":
        if not is_nonempty_string(selected_route_id) or not re.fullmatch(
            r"R-[A-Z0-9]+", selected_route_id.strip()
        ):
            errors.append(
                f"{comment_id}.route_decision: SELECTED requires selected_route_id like R-A."
            )
    elif selected_route_id is not None:
        errors.append(
            f"{comment_id}.route_decision: {selection_state} requires selected_route_id=null."
        )
    return selection_state


def validate_absence_checks(comment_id: str, value: Any, errors: list[str]) -> None:
    """Validate explicit literal checks; legacy negative_searches stay annotations."""
    if not isinstance(value, list) or not value:
        errors.append(f"{comment_id}: absence_checks must be a nonempty array when present.")
        return
    for index, check in enumerate(value, 1):
        prefix = f"{comment_id}.absence_checks[{index}]"
        if not isinstance(check, dict):
            errors.append(f"{prefix}: must be an object.")
            continue
        if set(check) - {"file", "literal", "scope"}:
            errors.append(f"{prefix}: only file, literal and optional scope are supported.")
        for field in ("file", "literal"):
            if not is_nonempty_string(check.get(field)):
                errors.append(f"{prefix}: {field} must be a nonempty string.")
        if is_nonempty_string(check.get("file")) and Path(check["file"]).is_absolute():
            errors.append(f"{prefix}: file must be relative to --repo.")
        if "scope" in check:
            scope = check["scope"]
            if (not isinstance(scope, dict) or set(scope) != {"start_anchor", "end_anchor"}
                    or not all(is_nonempty_string(scope.get(key))
                               for key in ("start_anchor", "end_anchor"))):
                errors.append(f"{prefix}: scope requires only nonempty start_anchor and end_anchor.")
            elif scope["start_anchor"] == scope["end_anchor"]:
                errors.append(f"{prefix}: scope anchors must differ.")


def literal_positions(text: str, literal: str) -> list[int]:
    """Include overlapping occurrences so an ambiguous delimiter cannot look unique."""
    positions = []
    position = text.find(literal)
    while position != -1:
        positions.append(position)
        position = text.find(literal, position + 1)
    return positions


def check_absences(comments: list, base_dir: Path | None,
                   errors: list[str], warnings: list[str]) -> list[dict[str, Any]]:
    findings = []
    for item in comments:
        if not isinstance(item, dict) or not isinstance(item.get("absence_checks"), list):
            continue
        terminal = item.get("status") in {"RESOLVED", "OBSOLETE_SCOPE"}
        for index, check in enumerate(item["absence_checks"], 1):
            prefix = f"{item.get('id')}.absence_checks[{index}]"
            structural_errors: list[str] = []
            validate_absence_checks(str(item.get("id")), [check], structural_errors)
            if structural_errors:
                continue  # Already reported by validate_comment.
            finding = {"comment_id": item.get("id"), "check_index": index,
                       "file": check["file"], "scope": "ANCHOR_RANGE" if "scope" in check else "FILE",
                       "outcome": "UNVERIFIED"}
            findings.append(finding)
            if base_dir is None:
                message = f"{prefix}: not executed; --repo is required for absence verification."
                (errors if terminal else warnings).append(message)
                continue
            path = (base_dir / check["file"]).resolve()
            if not path.is_relative_to(base_dir):
                errors.append(f"{prefix}: file escapes the evidence repository.")
                continue
            if not path.is_file():
                errors.append(f"{prefix}: file does not exist: {check['file']}.")
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as exc:
                errors.append(f"{prefix}: could not read UTF-8 text: {type(exc).__name__}.")
                continue
            if "scope" in check:
                scope = check["scope"]
                starts = literal_positions(text, scope["start_anchor"])
                ends = literal_positions(text, scope["end_anchor"])
                if len(starts) != 1 or len(ends) != 1:
                    errors.append(f"{prefix}: each scope anchor must occur exactly once in the file.")
                    continue
                if starts[0] + len(scope["start_anchor"]) > ends[0]:
                    errors.append(f"{prefix}: scope anchors are reversed or overlap.")
                    continue
                # Include the start delimiter, exclude the end delimiter.
                text = text[starts[0]:ends[0]]
            count = len(literal_positions(text, check["literal"]))
            finding.update(outcome="FOUND" if count else "PASS", occurrence_count=count)
            if count:
                message = f"{prefix}: expected absence failed; {count} literal occurrence(s) remain in scope."
                (errors if terminal else warnings).append(message)
    return findings


def validate_comment(item: Any, index: int, errors: list[str], warnings: list[str]) -> str | None:
    if not isinstance(item, dict):
        errors.append(f"comments[{index}]: must be an object.")
        return None
    comment_id = item.get("id")
    if not is_nonempty_string(comment_id):
        errors.append(f"comments[{index}]: id is required.")
        return None
    comment_id = comment_id.strip().upper()
    if not re.fullmatch(r"[A-Z]+\d+", comment_id):
        errors.append(f"{comment_id}: id must look like R1 or C33.")
    if not is_nonempty_string(item.get("reviewer")):
        errors.append(f"{comment_id}: reviewer is required.")
    if not is_nonempty_string(item.get("requirement")):
        errors.append(f"{comment_id}: requirement is required.")

    status = item.get("status")
    if status not in STATUSES:
        errors.append(f"{comment_id}: status must be one of {sorted(STATUSES)}.")
        return comment_id

    if "absence_checks" in item:
        validate_absence_checks(comment_id, item["absence_checks"], errors)
    if nonempty_list(item.get("negative_searches")):
        warnings.append(f"{comment_id}: legacy negative_searches are annotations, not executed checks; "
                        "use scoped absence_checks for literal verification.")

    work_types = item.get("work_types")
    if "work_types" in item:
        if (not isinstance(work_types, list) or not work_types or
                not all(isinstance(value, str) and value in WORK_TYPES for value in work_types)):
            errors.append(f"{comment_id}: work_types must be a nonempty array of {sorted(WORK_TYPES)}.")
        elif len(set(work_types)) != len(work_types):
            errors.append(f"{comment_id}: work_types must not contain duplicates.")
    if "source_id" in item and not is_nonempty_string(item["source_id"]):
        errors.append(f"{comment_id}: source_id must be a nonempty original-source identifier.")
    if "deferred_until" in item and item["deferred_until"] is not None:
        if not is_nonempty_string(item["deferred_until"]):
            errors.append(f"{comment_id}: deferred_until must be a nonempty phase/trigger or null.")
        if status in {"RESOLVED", "OBSOLETE_SCOPE"}:
            errors.append(f"{comment_id}: {status} cannot retain deferred work.")

    severity = item.get("severity")
    if severity not in SEVERITIES:
        errors.append(f"{comment_id}: severity must be one of {sorted(SEVERITIES)}.")

    rubric_outcomes = validate_rubric_findings(
        comment_id,
        item.get("rubric_findings"),
        errors,
    )
    route_selection_state = validate_route_decision_link(
        comment_id,
        item.get("route_decision"),
        errors,
    )

    evidence = item.get("evidence", [])
    validate_evidence(comment_id, evidence, errors)
    open_actions = item.get("open_actions", [])
    if not isinstance(open_actions, list) or not all(is_nonempty_string(x) for x in open_actions):
        errors.append(f"{comment_id}: open_actions must be an array of non-empty strings.")
        open_actions = []
    if is_nonempty_string(item.get("deferred_until")) and not open_actions:
        errors.append(f"{comment_id}: deferred work requires an explicit open action.")

    if status == "RESOLVED":
        if not nonempty_list(evidence):
            errors.append(f"{comment_id}: RESOLVED requires direct current evidence.")
        if open_actions:
            errors.append(f"{comment_id}: RESOLVED cannot retain open_actions.")
        unresolved = sorted(
            {outcome for outcome in rubric_outcomes if outcome in {"PARTIAL", "FAIL", "UNVERIFIABLE"}}
        )
        if unresolved:
            errors.append(
                f"{comment_id}: RESOLVED cannot retain unresolved rubric outcomes: "
                f"{', '.join(unresolved)}."
            )
        if route_selection_state in {
            "AWAITING_USER_APPROVAL",
            "NEEDS_HUMAN_DECISION",
            "BLOCKED",
        }:
            errors.append(
                f"{comment_id}: RESOLVED cannot retain route state {route_selection_state}."
            )
    elif status == "PARTIAL":
        if not nonempty_list(evidence):
            errors.append(f"{comment_id}: PARTIAL requires evidence of completed portions.")
        if not open_actions:
            errors.append(f"{comment_id}: PARTIAL requires at least one open action.")
    elif status == "OPEN" and not open_actions:
        errors.append(f"{comment_id}: OPEN requires at least one open action.")
    elif status == "OBSOLETE_SCOPE":
        if not nonempty_list(item.get("deletion_evidence")):
            errors.append(f"{comment_id}: OBSOLETE_SCOPE requires deletion_evidence.")
        if not (nonempty_list(item.get("negative_searches")) or nonempty_list(item.get("absence_checks"))):
            errors.append(f"{comment_id}: OBSOLETE_SCOPE requires negative_searches or absence_checks.")
        if open_actions:
            errors.append(f"{comment_id}: OBSOLETE_SCOPE cannot retain open_actions.")
    elif status == "BLOCKED" and not nonempty_list(item.get("blockers")):
        errors.append(f"{comment_id}: BLOCKED requires blockers.")
    elif status == "NEEDS_DECISION" and not nonempty_list(item.get("decision_options")):
        errors.append(f"{comment_id}: NEEDS_DECISION requires decision_options.")

    affected = item.get("affected_sections", [])
    if not isinstance(affected, list) or not all(is_nonempty_string(x) for x in affected):
        errors.append(f"{comment_id}: affected_sections must be an array of non-empty strings.")
    elif not affected:
        warnings.append(f"{comment_id}: affected_sections is empty.")

    dependencies = item.get("dependencies", [])
    if not isinstance(dependencies, list) or not all(is_nonempty_string(x) for x in dependencies):
        errors.append(f"{comment_id}: dependencies must be an array of non-empty strings.")
    return comment_id


def validate_document(
    document: Any, expected: Iterable[str], evidence_base_dir: Path | None = None
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(document, dict):
        return {"valid": False, "errors": ["Ledger root must be a JSON object."], "warnings": []}
    comments = document.get("comments")
    if not isinstance(comments, list):
        return {"valid": False, "errors": ["Ledger must contain a comments array."], "warnings": []}

    ids: list[str] = []
    for index, item in enumerate(comments):
        comment_id = validate_comment(item, index, errors, warnings)
        if comment_id:
            ids.append(comment_id)

    duplicates = sorted(identifier for identifier, count in collections.Counter(ids).items() if count > 1)
    if duplicates:
        errors.append(f"Duplicate comment IDs: {', '.join(duplicates)}.")

    expected_ids = list(expected)
    if expected_ids:
        missing = [identifier for identifier in expected_ids if identifier not in ids]
        unexpected = [identifier for identifier in ids if identifier not in expected_ids]
        if missing:
            errors.append(f"Missing expected IDs: {', '.join(missing)}.")
        if unexpected:
            errors.append(f"Unexpected IDs: {', '.join(unexpected)}.")

    actual_counts = collections.Counter(
        item.get("status") for item in comments if isinstance(item, dict) and item.get("status") in STATUSES
    )
    counts = {status: actual_counts.get(status, 0) for status in sorted(STATUSES)}
    if sum(counts.values()) != len(comments):
        errors.append("Status counts do not equal the number of comment records.")

    reported = document.get("reported_counts")
    if reported is not None:
        if not isinstance(reported, dict):
            errors.append("reported_counts must be an object when present.")
        else:
            normalized_reported = {status: reported.get(status, 0) for status in sorted(STATUSES)}
            if normalized_reported != counts:
                errors.append(
                    "reported_counts does not match mechanical counts: "
                    f"reported={normalized_reported}, actual={counts}."
                )

    known_ids = set(ids)
    for item in comments:
        if not isinstance(item, dict) or not is_nonempty_string(item.get("id")):
            continue
        comment_id = item["id"].strip().upper()
        for dependency in item.get("dependencies", []) if isinstance(item.get("dependencies", []), list) else []:
            dep = dependency.strip().upper()
            if re.fullmatch(r"[A-Z]+\d+", dep) and dep not in known_ids:
                errors.append(f"{comment_id}: dependency {dependency!r} is not present in the ledger.")

    checked_anchors = 0
    if evidence_base_dir is not None:
        base_dir = evidence_base_dir.resolve()
        for item in comments:
            if not isinstance(item, dict) or not isinstance(item.get("evidence"), list):
                continue
            for entry in item["evidence"]:
                if not isinstance(entry, dict) or not all(
                    is_nonempty_string(entry.get(field)) for field in ("file", "anchor")
                ):
                    continue
                path = (base_dir / entry["file"]).resolve()
                prefix = f"{item.get('id')}.evidence"
                if not path.is_relative_to(base_dir):
                    errors.append(f"{prefix}: file escapes the evidence repository.")
                    continue
                if not path.is_file():
                    errors.append(f"{prefix}: file does not exist: {entry['file']}.")
                    continue
                try:
                    text = path.read_text(encoding="utf-8-sig")
                except UnicodeError:
                    warnings.append(f"{prefix}: binary artifact needs manual anchor verification: {entry['file']}.")
                    continue
                except OSError as exc:
                    errors.append(f"{prefix}: could not read evidence: {type(exc).__name__}.")
                    continue
                if entry["anchor"] not in text:
                    errors.append(f"{prefix}: anchor is absent from {entry['file']}.")
                else:
                    checked_anchors += 1

    absence_findings = check_absences(
        comments, evidence_base_dir.resolve() if evidence_base_dir is not None else None,
        errors, warnings,
    )
    checked_absences = sum(finding["outcome"] in {"PASS", "FOUND"} for finding in absence_findings)
    scope = "LOCAL_TEXT_ANCHORS" if evidence_base_dir is not None else "STRUCTURE_ONLY"
    if evidence_base_dir is not None and absence_findings:
        scope = "LOCAL_TEXT_ANCHORS_AND_ABSENCE_CHECKS"
    return {
        "valid": not errors,
        "comment_count": len(comments),
        "counts": counts,
        "errors": errors,
        "warnings": warnings,
        "verification_scope": scope,
        "checked_anchor_count": checked_anchors,
        "checked_absence_count": checked_absences,
        "passed_absence_count": sum(finding["outcome"] == "PASS" for finding in absence_findings),
        "absence_check_results": absence_findings,
    }


def markdown_text(value: Any) -> str:
    """Render ledger strings as text, never as author-supplied Markdown/HTML."""
    text = html.escape(str(value), quote=False).replace("\\", "\\\\")
    for character in "`*_[]":
        text = text.replace(character, "\\" + character)
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # Protect block syntax only where it can act as syntax. Periods and hyphens
    # in ordinary prose (Reviewer A, per-image) remain readable in the source.
    lines = [re.sub(r"^(\s{0,3})(#{1,6}(?=\s|$)|[-+](?=\s)|\d+[.)](?=\s))",
                    lambda match: match[1] + ("\\" + match[2] if not match[2][0].isdigit()
                                               else match[2][:-1] + "\\" + match[2][-1]),
                    line) for line in lines]
    return "<br>".join(lines)


def render_markdown(document: dict, result: dict, source_sha256: str) -> str:
    if not result.get("valid"):
        raise ValueError("Cannot render an invalid ledger.")
    rows = [
        "# Reviewer ledger", "",
        "Generated view of the canonical JSON; edit the JSON and generate a new view.",
        f"Source SHA-256: `{source_sha256}`.",
        f"Validation scope: `{result['verification_scope']}`. Scientific support is not certified.",
        "", "| Status | Count |", "| --- | ---: |",
    ]
    rows.extend(f"| {status} | {count} |" for status, count in result["counts"].items())
    rows.extend([f"| TOTAL | {result['comment_count']} |", ""])
    if result.get("absence_check_results"):
        rows.extend(["## Literal absence checks", "",
                     f"Executed: {result['checked_absence_count']}; passed: {result['passed_absence_count']}.",
                     "Exact, case-sensitive text checks within declared files/ranges; semantic equivalents require review.", ""])
        rows.extend("- " + markdown_text(json.dumps(finding, ensure_ascii=False))
                    for finding in result["absence_check_results"])
        rows.append("")
    if result["warnings"]:
        rows.extend(["## Validation warnings", ""])
        rows.extend(f"- {markdown_text(warning)}" for warning in result["warnings"])
        rows.append("")
    for item in document["comments"]:
        rows.extend([
            f"## {item['id'].strip().upper()}", "",
            f"Reviewer: {markdown_text(item['reviewer'])}", "",
            f"Status: **{item['status']}**; severity: {item['severity']}.", "",
            f"Requirement: {markdown_text(item['requirement'])}", "",
        ])
        for field, label in (("source_id", "Original source ID"),
                             ("deferred_until", "Deferred until")):
            if item.get(field):
                rows.extend([f"{label}: {markdown_text(item[field])}", ""])
        if item.get("work_types"):
            rows.extend(["Work types: " + ", ".join(item['work_types']), ""])
        # Include every remaining field; route approval, evidence and pending work
        # must not vanish from the human-readable view.
        displayed = {"id", "reviewer", "status", "severity", "requirement",
                     "source_id", "deferred_until", "work_types"}
        for field, value in item.items():
            if field in displayed:
                continue
            rows.extend([f"**{markdown_text(field)}:**", ""])
            values = value if isinstance(value, list) else [value]
            if not values:
                rows.append("None recorded.")
            for entry in values:
                content = json.dumps(entry, ensure_ascii=False) if isinstance(entry, (dict, list)) else entry
                rows.append(f"- {markdown_text(content)}")
            rows.append("")
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a scientific-paper reviewer ledger")
    parser.add_argument("ledger", help="Path to review_ledger.json")
    parser.add_argument("--expected", default="", help='Expected IDs, e.g. "R1-R8,C1-C33"')
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--repo", help="Evidence root; verify literal anchors and explicit scoped absence_checks")
    parser.add_argument("--markdown-output", help="New Markdown view path; written only after validation, never overwritten")
    args = parser.parse_args()

    try:
        expected = expand_expected(args.expected)
        path = Path(args.ledger).expanduser().resolve()
        source_bytes = path.read_bytes()
        document = json.loads(source_bytes.decode("utf-8-sig"))
        result = validate_document(document, expected, Path(args.repo) if args.repo else None)
        result.update({"schema": "academic-review-ledger-guard/1.4", "ledger": str(path)})
        if args.markdown_output and result["valid"]:
            output = Path(args.markdown_output).expanduser().resolve()
            if output.exists() or output == path:
                raise FileExistsError("Markdown output exists; choose a new view path.")
            source_sha256 = hashlib.sha256(source_bytes).hexdigest()
            rendered = render_markdown(document, result, source_sha256)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8", newline="\n") as target:
                target.write(rendered)
            result.update(markdown_output=str(output), source_sha256=source_sha256)
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None), flush=True)
        return 0 if result["valid"] else 1
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "schema": "academic-review-ledger-guard/1.4",
                    "valid": False,
                    "errors": [f"{type(exc).__name__}: {exc}"],
                    "warnings": [],
                },
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            ),
            flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
