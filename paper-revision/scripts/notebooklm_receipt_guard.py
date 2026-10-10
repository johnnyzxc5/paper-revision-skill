#!/usr/bin/env python3
"""Validate saved NotebookLM wrapper artifacts used by a route decision.

Each receipt binds a logical query ID to its exact prompt, selected sources,
resolved notebook, and saved wrapper JSON.  This prevents a route table from
claiming NotebookLM evaluation when no successful query artifact exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROLES = {"project", "theory", "writing"}
CONSULTATION_STATES = {"COMPLETED", "BLOCKED", "NOT_REQUIRED"}
ROUTE_REQUIRED_LABELS = {
    "project": (
        "SNAPSHOT_MATCH:",
        "IN_FORCE_CONSTRAINTS:",
        "REVIEWER_REQUIREMENTS:",
        "RIPPLE_TARGETS:",
        "MISSING_LOCAL_EVIDENCE:",
    ),
    "theory": (
        "ROUTE_FINDINGS:",
        "TECHNICALLY_PREFERRED_ROUTE:",
        "UNSUPPORTED_PROPOSITIONS:",
        "MISSING_EVIDENCE:",
        "SOURCE_USE_REPORT:",
        "ADDITIONAL_ROUTE:",
    ),
    "writing": (
        "ROUTE_FINDINGS:",
        "RHETORICALLY_PREFERRED_ROUTE:",
        "APPLICABLE_PAPER_RUBRIC_LAYERS:",
        "SOURCE_USE_REPORT:",
        "OWNERSHIP_OR_SCOPE_RISKS:",
        "ADDITIONAL_ROUTE:",
    ),
}
CANDIDATE_REQUIRED_LABELS = {
    "theory": ("VERDICT:", "FAILED_CRITERIA:", "EVIDENCE:", "REQUIRED_CHANGE:"),
    "writing": ("VERDICT:", "FAILED_CRITERIA:", "EVIDENCE:", "REQUIRED_CHANGE:"),
}
ROLE_CRITERIA = {
    "theory": {"RG2", "RG3", "RG6", "RG7"},
    "writing": {"RG1", "RG4", "RG7", "RG8"},
}
OUTCOMES = {"PASS", "PARTIAL", "FAIL", "NOT_APPLICABLE", "UNVERIFIABLE"}
CANDIDATE_VERDICTS = {"PASS", "FAIL", "INSUFFICIENT_EVIDENCE"}
ROUTE_ID_PATTERN = re.compile(r"R-[A-Z0-9]+")
ROUTE_OUTCOME_ROW = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(R-[A-Z0-9]+)\s*\|\s*(RG[1-9])\s*\|\s*"
    r"(PASS|PARTIAL|FAIL|NOT_APPLICABLE|UNVERIFIABLE)\b"
)
LEGACY_ROUTE_TOKEN = re.compile(r"(?im)^\s*(?:[-*]\s+)?\[?(R\d+)\s*(?:\||:|\b(?:calibrates|repairs|removes|adds)\b)")
PREFERRED_ROUTE_ASSIGNMENT = re.compile(
    r"(?im)^[ \t]*(TECHNICALLY_PREFERRED_ROUTE|RHETORICALLY_PREFERRED_ROUTE)"
    r"[ \t]*:[ \t]*(\S[^\r\n]*)$"
)
PREFILLED_OUTPUT_FIELD = re.compile(
    r"(?im)^[ \t]*(UNSUPPORTED_PROPOSITIONS|MISSING_EVIDENCE|ADDITIONAL_ROUTE|"
    r"OWNERSHIP_OR_SCOPE_RISKS|FAILED_CRITERIA|REQUIRED_CHANGE)"
    r"[ \t]*:[ \t]*(\S[^\r\n]*)$"
)
ROUTE_RECOMMENDATION_LINE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?R-[A-Z0-9]+\b[^\n]*\b(?:recommended|preferred)\b"
)


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: Any, *, allow_empty: bool = True) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(nonempty_string(item) for item in value)
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def resolve_relative(base_dir: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (base_dir / path).resolve()


def normalized_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").strip()


def is_placeholder(value: str) -> bool:
    clean = value.strip()
    return (
        not clean
        or clean.startswith("[")
        or clean.startswith("<")
        or "[..." in clean
        or "<..." in clean
    )


def normalize_candidate_text(value: str) -> str:
    """Compare the LaTeX shown in prompts across Windows and Unix line endings."""
    return value.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")


def labeled_fields(text: str) -> dict[str, list[str]]:
    """Preserve duplicate labels and multiline evidence instead of choosing a verdict."""
    pattern = re.compile(
        r"(?m)^[ \t]*(?:\*\*)?([A-Z][A-Z0-9_]+)(?::\*\*|\*\*:|:)[ \t]*(.*)$"
    )
    matches = list(pattern.finditer(text))
    fields: dict[str, list[str]] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        value = (match.group(2) + text[match.end():end]).strip().strip("*").strip()
        fields.setdefault(match.group(1), []).append(value)
    return fields


def candidate_from_prompt(prompt_text: str) -> str | None:
    """Require exactly one literal candidate block; a digest alone is insufficient."""
    normalized = prompt_text.replace("\r\n", "\n").replace("\r", "\n")
    if len(re.findall(r"(?m)^REVISED_TEXT_BEGIN[ \t]*$", normalized)) != 1:
        return None
    if len(re.findall(r"(?m)^REVISED_TEXT_END[ \t]*$", normalized)) != 1:
        return None
    match = re.search(
        r"(?ms)^REVISED_TEXT_BEGIN[ \t]*\n(.*?)^REVISED_TEXT_END[ \t]*$", normalized
    )
    return normalize_candidate_text(match.group(1)) if match else None


def validate_candidate_answer(answer: str, references: Any) -> list[str]:
    errors: list[str] = []
    fields = labeled_fields(answer)
    for label in CANDIDATE_REQUIRED_LABELS["writing"]:
        key = label.rstrip(":")
        if len(fields.get(key, [])) != 1:
            errors.append(f"Candidate answer requires exactly one {key} field.")
    verdicts = fields.get("VERDICT", [])
    verdict = verdicts[0].strip().rstrip(".") if len(verdicts) == 1 else None
    if verdict not in CANDIDATE_VERDICTS:
        errors.append("Candidate answer has no unique valid verdict.")
    if verdict == "PASS":
        for key in ("FAILED_CRITERIA", "REQUIRED_CHANGE"):
            values = fields.get(key, [])
            if len(values) != 1 or values[0].strip().rstrip(".").upper() != "NONE":
                errors.append(f"PASS contradicts {key}; its value must be NONE.")
        evidence_values = fields.get("EVIDENCE", [])
        evidence = evidence_values[0] if len(evidence_values) == 1 else ""
        if not evidence or evidence.strip().rstrip(".").upper() in {
            "NONE", "N/A", "INSUFFICIENT_EVIDENCE", "UNVERIFIABLE"
        }:
            errors.append("A source-grounded PASS requires non-empty evidence.")
        has_references = isinstance(references, list) and bool(references)
        has_markers = bool(re.search(r"\[\d+(?:\s*[,\-]\s*\d+)*\]", evidence))
        if not has_references and not has_markers:
            errors.append("PASS requires returned references or identifiable evidence citation markers.")
    return errors


def validate_prompt_neutrality(
    prompt_text: str,
    *,
    phase: str,
    role: str,
    route_ids: set[str],
) -> list[str]:
    """Reject prompts that prescribe the verdict they claim to audit."""
    errors: list[str] = []
    if phase not in {"route", "candidate"}:
        return ["phase must be route or candidate."]
    if role not in ROLES:
        return [f"role must be one of {sorted(ROLES)}."]

    if phase == "route" and role in {"theory", "writing"}:
        invalid_route_ids = sorted(
            route_id for route_id in route_ids if not ROUTE_ID_PATTERN.fullmatch(route_id)
        )
        if invalid_route_ids:
            errors.append(
                "Route IDs must use the R-A form, not R1/R2: "
                + ", ".join(invalid_route_ids)
            )
        route_sections = re.findall(
            r"(?ms)^(?:CANDIDATE_ROUTES|ROUTES):[ \t]*(.*?)(?=^[A-Z][A-Z0-9_ ]*:|\Z)",
            prompt_text,
        )
        legacy_tokens = sorted(set(LEGACY_ROUTE_TOKEN.findall("\n".join(route_sections))))
        if legacy_tokens:
            errors.append(
                "Prompt contains invalid route tokens; use R-A/R-B: "
                + ", ".join(legacy_tokens)
            )
        missing_routes = sorted(route_id for route_id in route_ids if route_id not in prompt_text)
        if missing_routes:
            errors.append("Prompt omits proposed routes: " + ", ".join(missing_routes))

        prescribed_rows = [" | ".join(match) for match in ROUTE_OUTCOME_ROW.findall(prompt_text)]
        if prescribed_rows:
            errors.append(
                "Prompt preassigns route outcomes instead of requesting an audit: "
                + "; ".join(prescribed_rows[:4])
            )
        for label, value in PREFERRED_ROUTE_ASSIGNMENT.findall(prompt_text):
            if not is_placeholder(value):
                errors.append(f"Prompt preassigns {label}: {value.strip()}")
        for label, value in PREFILLED_OUTPUT_FIELD.findall(prompt_text):
            if not is_placeholder(value):
                errors.append(f"Prompt prefills output field {label}: {value.strip()}")
        if ROUTE_RECOMMENDATION_LINE.search(prompt_text):
            errors.append(
                "Prompt labels a candidate route as recommended/preferred before evaluation."
            )

        required_criteria = ROLE_CRITERIA.get(role, set())
        missing_criteria = sorted(
            criterion for criterion in required_criteria if criterion not in prompt_text
        )
        if missing_criteria:
            errors.append(
                f"Prompt omits {role} route criteria: {', '.join(missing_criteria)}."
            )

    if phase == "candidate" and role in {"theory", "writing"}:
        if len(re.findall(r"(?m)^CANDIDATE_SHA256:[ \t]*[0-9a-f]{64}[ \t]*$", prompt_text)) != 1:
            errors.append("Candidate prompt requires exactly one lowercase CANDIDATE_SHA256.")
        source_mode = role == "writing" and re.findall(r"(?m)^INPUT_MODE: SOURCE$", prompt_text) == ["INPUT_MODE: SOURCE"]
        if source_mode:
            for label in ("TARGET_SOURCE_ID", "RUBRIC_SOURCE_ID", "COVERAGE_UNITS"):
                if len(re.findall(rf"(?m)^{label}: \S[^\n]*$", prompt_text)) != 1:
                    errors.append(f"Source candidate prompt requires exactly one {label}.")
            if re.findall(r"(?m)^REVIEW_MODE: (\S+)$", prompt_text) != ["CANDIDATE_AUDIT"]:
                errors.append("Source candidate prompt requires REVIEW_MODE: CANDIDATE_AUDIT.")
        elif not candidate_from_prompt(prompt_text):
            errors.append("Candidate prompt requires one non-empty REVISED_TEXT_BEGIN/END block.")
        for value in re.findall(r"(?im)^[ \t]*VERDICT[ \t]*:[ \t]*([^\r\n]*)", prompt_text):
            if is_placeholder(value):
                continue
            allowed = {part.strip() for part in value.split("|")}
            if not (len(allowed) > 1 and allowed <= CANDIDATE_VERDICTS):
                errors.append("Candidate prompt preassigns VERDICT.")
        for label, value in PREFILLED_OUTPUT_FIELD.findall(prompt_text):
            if not is_placeholder(value):
                errors.append(f"Candidate prompt prefills output field {label}: {value.strip()}")

    return errors


def result_for_query(payload: Any, query_id: str) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("command") == "ask":
        result = payload.get("result")
        return result if isinstance(result, dict) and result.get("query_id") == query_id else None
    if payload.get("command") == "batch":
        results = payload.get("results")
        if isinstance(results, list):
            matches = [
                item
                for item in results
                if isinstance(item, dict) and item.get("query_id") == query_id
            ]
            return matches[0] if len(matches) == 1 else None
    return None


def validate_receipt(
    receipt: Any,
    index: int,
    base_dir: Path,
    route_ids: set[str],
    errors: list[str],
    *,
    phase: str = "route",
    candidate_sha256: str | None = None,
    candidate_text: str | None = None,
    consultation_field: str = "notebooklm_consultation",
) -> tuple[str | None, str | None, bool, str]:
    prefix = f"{consultation_field}.receipts[{index}]"
    starting_error_count = len(errors)
    if not isinstance(receipt, dict):
        errors.append(f"{prefix}: must be an object.")
        return None, None, False, ""

    query_id = receipt.get("query_id")
    if not nonempty_string(query_id):
        errors.append(f"{prefix}.query_id is required.")
        query_id = None
    else:
        query_id = query_id.strip()
        if query_id == "single":
            errors.append(f"{prefix}.query_id: 'single' is not an auditable logical ID.")
        if phase == "candidate" and not re.fullmatch(r".+-r[12]", query_id):
            errors.append(f"{prefix}.query_id: candidate audits require a bounded -r1 or -r2 suffix.")

    role = receipt.get("role")
    if role not in ROLES:
        errors.append(f"{prefix}.role must be one of {sorted(ROLES)}.")
        role = None

    notebook_id = receipt.get("notebook_id")
    if not nonempty_string(notebook_id):
        errors.append(f"{prefix}.notebook_id is required.")

    source_ids = receipt.get("source_ids")
    if not string_list(source_ids, allow_empty=True):
        errors.append(f"{prefix}.source_ids must be an array of strings.")
        source_ids = []
    if role in {"project", "writing"} and not source_ids:
        errors.append(f"{prefix}: {role} route queries require explicit source IDs.")

    prompt_file = receipt.get("prompt_file")
    output_file = receipt.get("output_file")
    output_sha256 = receipt.get("output_sha256")
    if not nonempty_string(prompt_file):
        errors.append(f"{prefix}.prompt_file is required.")
    if not nonempty_string(output_file):
        errors.append(f"{prefix}.output_file is required.")
    if not isinstance(output_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", output_sha256):
        errors.append(f"{prefix}.output_sha256 must be a lowercase SHA-256 digest.")

    if not (nonempty_string(prompt_file) and nonempty_string(output_file)):
        return query_id, role, False, ""

    try:
        prompt_path = resolve_relative(base_dir, prompt_file)
        prompt_text = normalized_prompt(prompt_path)
    except OSError as exc:
        errors.append(f"{prefix}: could not read prompt_file: {type(exc).__name__}: {exc}")
        return query_id, role, False, ""
    task_ids = re.findall(r"(?m)^TASK_ID:[ \t]*(\S+)[ \t]*$", prompt_text)
    if query_id and task_ids != [query_id]:
        errors.append(f"{prefix}: prompt_file must declare exactly one matching TASK_ID.")
    if phase == "candidate":
        declared_hashes = re.findall(r"(?m)^CANDIDATE_SHA256:[ \t]*([0-9a-f]{64})[ \t]*$", prompt_text)
        if not isinstance(candidate_sha256, str) or declared_hashes != [candidate_sha256]:
            errors.append(f"{prefix}: prompt_file must declare the exact candidate SHA-256.")
        source_mode = role == "writing" and re.findall(r"(?m)^INPUT_MODE: SOURCE$", prompt_text) == ["INPUT_MODE: SOURCE"]
        structured_review = role == "writing" and (source_mode or re.findall(r"(?m)^REVIEW_CONTRACT: exact-block/v1$", prompt_text) == ["REVIEW_CONTRACT: exact-block/v1"])
        if structured_review:
            try:
                import writing_review_guard as writing_reviews
                review_path = resolve_relative(base_dir, receipt["writing_review_file"])
                review = writing_reviews.load(review_path)
                checked = writing_reviews.validate(review, review_path.parent)
                if not checked["passed"] or review.get("mode") != "CANDIDATE_AUDIT" or review.get("candidate_sha256") != candidate_sha256:
                    errors.append(f"{prefix}: exact-block review is not a passing full audit of this candidate: {checked['errors']}")
                matches = [query for query in review.get("queries", []) if query.get("query_id") == query_id]
                if len(matches) != 1 or resolve_relative(review_path.parent, matches[0]["prompt_file"]).resolve() != prompt_path.resolve() or resolve_relative(review_path.parent, matches[0]["output_file"]).resolve() != resolve_relative(base_dir, output_file).resolve() or matches[0].get("source_ids") != source_ids:
                    errors.append(f"{prefix}: source review does not bind this exact receipt/prompt/source scope.")
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(f"{prefix}: exact-block candidate requires a valid writing_review_file: {exc}")
        else:
            prompted_candidate = candidate_from_prompt(prompt_text)
            if candidate_text is None or prompted_candidate != normalize_candidate_text(candidate_text):
                errors.append(f"{prefix}: literal REVISED_TEXT block does not match the candidate file.")
    prompt_errors = validate_prompt_neutrality(
        prompt_text,
        phase=phase,
        role=role or "",
        route_ids=route_ids,
    )
    errors.extend(f"{prefix}: {message}" for message in prompt_errors)
    try:
        output_path = resolve_relative(base_dir, output_file)
        superseded = sorted(output_path.parent.glob(output_path.name + ".superseded-*"))
        if superseded:
            errors.append(
                f"{prefix}: output_file has superseded predecessors; auditable receipts "
                "must use a new query ID and a new output path."
            )
        output_bytes = output_path.read_bytes()
        payload = json.loads(output_bytes.decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"{prefix}: could not read output_file: {type(exc).__name__}: {exc}")
        return query_id, role, False, ""

    if sha256_bytes(output_bytes) != output_sha256:
        errors.append(f"{prefix}: output_file SHA-256 does not match the receipt.")
    schema = payload.get("schema") if isinstance(payload, dict) else None
    if not isinstance(schema, str) or not schema.startswith("notebooklm-agent-wrapper/"):
        errors.append(f"{prefix}: output is not a NotebookLM wrapper document.")
    usable_envelope = isinstance(payload, dict) and (
        payload.get("status") == "success"
        or (payload.get("command") == "batch" and payload.get("status") == "partial")
    )
    if not usable_envelope:
        errors.append(f"{prefix}: wrapper must be successful or a partial batch with an individually successful result.")

    result = result_for_query(payload, query_id or "")
    if result is None:
        errors.append(f"{prefix}: output has no unique result for query_id={query_id!r}.")
        return query_id, role, False, ""
    if result.get("status") != "success" or not nonempty_string(result.get("answer")):
        errors.append(f"{prefix}: query result must be successful with a non-empty answer.")
    if result.get("notebook_id") != notebook_id:
        errors.append(f"{prefix}: resolved notebook_id does not match the receipt.")
    request = result.get("request")
    if not isinstance(request, dict):
        errors.append(f"{prefix}: result.request is missing.")
    else:
        expected_prompt_hash = sha256_bytes(prompt_text.encode("utf-8"))
        if request.get("question_sha256") != expected_prompt_hash:
            errors.append(f"{prefix}: prompt does not match result.request.question_sha256.")
        if request.get("source_ids") != source_ids:
            errors.append(f"{prefix}: selected source IDs do not match the wrapper request.")
    if not nonempty_string(result.get("retrieval_method")):
        errors.append(f"{prefix}: retrieval_method is required.")

    answer = result.get("answer", "")
    labels_by_role = (
        ROUTE_REQUIRED_LABELS if phase == "route" else CANDIDATE_REQUIRED_LABELS
    )
    if role in labels_by_role and isinstance(answer, str):
        missing_labels = [
            label
            for label in labels_by_role[role]
            if label.rstrip(":") not in labeled_fields(answer)
        ]
        if missing_labels:
            errors.append(f"{prefix}: answer is missing labels {', '.join(missing_labels)}.")
        if phase == "route" and role in {"theory", "writing"}:
            missing_routes = sorted(route_id for route_id in route_ids if route_id not in answer)
            if missing_routes:
                errors.append(
                    f"{prefix}: route audit does not mention routes {', '.join(missing_routes)}."
                )
        if phase == "candidate":
            errors.extend(
                f"{prefix}: {message}"
                for message in validate_candidate_answer(answer, result.get("references"))
            )

    return query_id, role, len(errors) == starting_error_count, answer if isinstance(answer, str) else ""


def validate_specialist_findings(
    findings: Any,
    verified_receipts: list[dict[str, str]],
    required_roles: list[str],
    route_ids: set[str],
    errors: list[str],
) -> None:
    prefix = "notebooklm_consultation.findings"
    if not isinstance(findings, list):
        errors.append(f"{prefix} must be an array.")
        return

    receipts_by_query = {item["query_id"]: item for item in verified_receipts}
    observed: set[tuple[str, str, str]] = set()
    for index, finding in enumerate(findings, 1):
        item_prefix = f"{prefix}[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{item_prefix} must be an object.")
            continue
        query_id = finding.get("query_id")
        role = finding.get("role")
        route_id = finding.get("route_id")
        criterion_id = finding.get("criterion_id")
        outcome = finding.get("outcome")
        evidence = finding.get("evidence")
        if not nonempty_string(query_id) or query_id not in receipts_by_query:
            errors.append(f"{item_prefix}.query_id must name a verified receipt.")
            continue
        receipt = receipts_by_query[query_id]
        if role != receipt["role"] or role not in ROLE_CRITERIA:
            errors.append(f"{item_prefix}.role does not match a theory/writing receipt.")
        if route_id not in route_ids:
            errors.append(f"{item_prefix}.route_id must name a proposed route.")
        if criterion_id not in ROLE_CRITERIA.get(role, set()):
            errors.append(f"{item_prefix}.criterion_id is not assigned to role {role!r}.")
        if outcome not in OUTCOMES:
            errors.append(f"{item_prefix}.outcome must be one of {sorted(OUTCOMES)}.")
        if not nonempty_string(evidence):
            errors.append(f"{item_prefix}.evidence is required.")
        key = (role, route_id, criterion_id)
        if key in observed:
            errors.append(f"{item_prefix}: duplicate specialist finding {key}.")
        observed.add(key)

        if all(nonempty_string(value) for value in (route_id, criterion_id, outcome)):
            pattern = re.compile(
                rf"{re.escape(route_id)}\s*\|\s*{re.escape(criterion_id)}\s*\|\s*{re.escape(outcome)}(?:\s*\||\b)",
                re.IGNORECASE,
            )
            if not pattern.search(receipt["answer"]):
                errors.append(
                    f"{item_prefix}: route/criterion/outcome triplet is absent from the raw answer."
                )

    for role in sorted(set(required_roles) & set(ROLE_CRITERIA)):
        for route_id in sorted(route_ids):
            missing = sorted(
                criterion
                for criterion in ROLE_CRITERIA[role]
                if (role, route_id, criterion) not in observed
            )
            if missing:
                errors.append(
                    f"{prefix}: {role} lacks {route_id} findings for {', '.join(missing)}."
                )


def validate_consultation(
    consultation: Any,
    base_dir: Path,
    route_ids: set[str],
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(consultation, dict):
        return {
            "valid": False,
            "status": None,
            "verified_query_ids": [],
            "verified_roles": [],
            "errors": ["notebooklm_consultation must be an object."],
        }

    status = consultation.get("status")
    if status not in CONSULTATION_STATES:
        errors.append(
            f"notebooklm_consultation.status must be one of {sorted(CONSULTATION_STATES)}."
        )

    required_roles = consultation.get("required_roles")
    if not string_list(required_roles, allow_empty=True):
        errors.append("notebooklm_consultation.required_roles must be an array of strings.")
        required_roles = []
    invalid_roles = sorted(set(required_roles) - ROLES)
    if invalid_roles:
        errors.append(f"Invalid required roles: {', '.join(invalid_roles)}.")
    if len(set(required_roles)) != len(required_roles):
        errors.append("notebooklm_consultation.required_roles contains duplicates.")

    reason = consultation.get("reason")
    if not nonempty_string(reason):
        errors.append("notebooklm_consultation.reason is required.")

    receipts = consultation.get("receipts")
    if not isinstance(receipts, list):
        errors.append("notebooklm_consultation.receipts must be an array.")
        receipts = []

    inspected: list[tuple[str | None, str | None, bool, str]] = []
    if status == "COMPLETED":
        if not required_roles:
            errors.append("COMPLETED requires at least one required role.")
        if not receipts:
            errors.append("COMPLETED requires at least one receipt.")
        for index, receipt in enumerate(receipts, 1):
            inspected.append(validate_receipt(receipt, index, base_dir, route_ids, errors))
    elif status in {"BLOCKED", "NOT_REQUIRED"}:
        if receipts:
            errors.append(f"{status} requires an empty receipts array.")
        if status == "NOT_REQUIRED" and required_roles:
            errors.append("NOT_REQUIRED requires an empty required_roles array.")

    declared_query_ids = [query_id for query_id, _, _, _ in inspected if query_id]
    if len(set(declared_query_ids)) != len(declared_query_ids):
        errors.append("Receipt query IDs must be unique.")
    verified = [
        {"query_id": query_id, "role": role, "answer": answer}
        for query_id, role, valid, answer in inspected
        if valid and query_id and role
    ]
    query_ids = [item["query_id"] for item in verified]
    roles = [item["role"] for item in verified]
    if status == "COMPLETED":
        missing_roles = sorted(set(required_roles) - set(roles))
        if missing_roles:
            errors.append(f"Missing successful receipts for roles: {', '.join(missing_roles)}.")
        validate_specialist_findings(
            consultation.get("findings"),
            verified,
            required_roles,
            route_ids,
            errors,
        )
    elif consultation.get("findings") not in ([], None):
        errors.append(f"{status} requires an empty findings array.")

    return {
        "valid": not errors,
        "status": status,
        "verified_query_ids": query_ids,
        "verified_roles": sorted(set(roles)),
        "errors": errors,
    }


def validate_candidate_consultation(
    consultation: Any,
    base_dir: Path,
    candidate_sha256: str,
    expected_roles: set[str],
    candidate_text: str | None = None,
) -> dict[str, Any]:
    """Validate NotebookLM audits of the exact candidate shown to the user."""
    field = "candidate_notebooklm_consultation"
    errors: list[str] = []
    if not isinstance(consultation, dict):
        return {
            "valid": False,
            "status": None,
            "verified_query_ids": [],
            "verified_roles": [],
            "errors": [f"{field} must be an object."],
        }

    status = consultation.get("status")
    if status not in CONSULTATION_STATES:
        errors.append(f"{field}.status must be one of {sorted(CONSULTATION_STATES)}.")
    required_roles = consultation.get("required_roles")
    if not string_list(required_roles, allow_empty=True):
        errors.append(f"{field}.required_roles must be an array of strings.")
        required_roles = []
    invalid_roles = sorted(set(required_roles) - set(CANDIDATE_REQUIRED_LABELS))
    if invalid_roles:
        errors.append(f"{field}.required_roles contains invalid roles: {', '.join(invalid_roles)}.")
    if set(required_roles) != expected_roles:
        errors.append(
            f"{field}.required_roles must match the expert roles used at route selection."
        )
    if len(set(required_roles)) != len(required_roles):
        errors.append(f"{field}.required_roles contains duplicates.")
    if consultation.get("candidate_sha256") != candidate_sha256:
        errors.append(f"{field}.candidate_sha256 does not match the candidate.")
    if not nonempty_string(consultation.get("reason")):
        errors.append(f"{field}.reason is required.")

    receipts = consultation.get("receipts")
    if not isinstance(receipts, list):
        errors.append(f"{field}.receipts must be an array.")
        receipts = []
    findings = consultation.get("findings")
    if not isinstance(findings, list):
        errors.append(f"{field}.findings must be an array.")
        findings = []

    inspected: list[tuple[str | None, str | None, bool, str]] = []
    if expected_roles:
        if status != "COMPLETED":
            errors.append(f"{field}.status must be COMPLETED for the selected route's experts.")
        if not receipts:
            errors.append(f"{field}.receipts must not be empty.")
        for index, receipt in enumerate(receipts, 1):
            inspected.append(
                validate_receipt(
                    receipt,
                    index,
                    base_dir,
                    set(),
                    errors,
                    phase="candidate",
                    candidate_sha256=candidate_sha256,
                    candidate_text=candidate_text,
                    consultation_field=field,
                )
            )
    else:
        if status != "NOT_REQUIRED":
            errors.append(f"{field}.status must be NOT_REQUIRED when no expert role applies.")
        if receipts or findings:
            errors.append(f"{field}: NOT_REQUIRED requires empty receipts and findings.")

    verified = [
        {"query_id": query_id, "role": role, "answer": answer}
        for query_id, role, valid, answer in inspected
        if valid and query_id and role
    ]
    query_ids = [item["query_id"] for item in verified]
    if len(set(query_ids)) != len(query_ids):
        errors.append(f"{field}: receipt query IDs must be unique.")
    verified_roles = {item["role"] for item in verified}
    missing_roles = sorted(expected_roles - verified_roles)
    if missing_roles:
        errors.append(f"{field}: missing successful receipts for {', '.join(missing_roles)}.")

    receipt_by_query = {item["query_id"]: item for item in verified}
    observed_roles: set[str] = set()
    for index, finding in enumerate(findings, 1):
        prefix = f"{field}.findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{prefix} must be an object.")
            continue
        query_id = finding.get("query_id")
        role = finding.get("role")
        verdict = finding.get("verdict")
        if not nonempty_string(query_id) or query_id not in receipt_by_query:
            errors.append(f"{prefix}.query_id must name a verified receipt.")
            continue
        receipt = receipt_by_query[query_id]
        if role != receipt["role"] or role not in expected_roles:
            errors.append(f"{prefix}.role does not match a required receipt.")
        if role in observed_roles:
            errors.append(f"{prefix}: duplicate final verdict for role {role!r}.")
        if nonempty_string(role):
            observed_roles.add(role)
        if verdict not in CANDIDATE_VERDICTS:
            errors.append(f"{prefix}.verdict must be one of {sorted(CANDIDATE_VERDICTS)}.")
        elif verdict != "PASS":
            errors.append(f"{prefix}: the exact candidate did not pass ({verdict}).")
        if not nonempty_string(finding.get("evidence")):
            errors.append(f"{prefix}.evidence is required.")
        raw_verdicts = [value.strip().rstrip(".") for value in labeled_fields(receipt["answer"]).get("VERDICT", [])]
        if verdict in CANDIDATE_VERDICTS and raw_verdicts != [verdict]:
            errors.append(f"{prefix}: unique verdict does not match the raw answer.")

    missing_findings = sorted(expected_roles - observed_roles)
    if missing_findings:
        errors.append(f"{field}: missing final PASS findings for {', '.join(missing_findings)}.")

    return {
        "valid": not errors,
        "status": status,
        "verified_query_ids": query_ids,
        "verified_roles": sorted(verified_roles),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate NotebookLM evidence receipts")
    parser.add_argument(
        "decision",
        nargs="?",
        help="Route-decision JSON containing notebooklm_consultation",
    )
    parser.add_argument(
        "--check-prompt",
        help="Preflight one NotebookLM prompt before sending it",
    )
    parser.add_argument("--phase", choices=("route", "candidate"), default="route")
    parser.add_argument("--role", choices=tuple(sorted(ROLES)))
    parser.add_argument(
        "--route",
        dest="route_ids",
        action="append",
        default=[],
        help="Expected route ID; repeat for each route",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        if args.check_prompt:
            if not args.role:
                parser.error("--check-prompt requires --role")
            prompt_path = Path(args.check_prompt).expanduser().resolve()
            prompt_text = normalized_prompt(prompt_path)
            errors = validate_prompt_neutrality(
                prompt_text,
                phase=args.phase,
                role=args.role,
                route_ids=set(args.route_ids),
            )
            result = {
                "schema": "notebooklm-prompt-integrity-guard/1.0",
                "valid": not errors,
                "phase": args.phase,
                "role": args.role,
                "prompt": str(prompt_path),
                "errors": errors,
            }
            print(
                json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None),
                flush=True,
            )
            return 0 if result["valid"] else 1
        if not args.decision:
            parser.error("decision is required unless --check-prompt is used")
        path = Path(args.decision).expanduser().resolve()
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        routes = document.get("routes", []) if isinstance(document, dict) else []
        route_ids = {
            route.get("id")
            for route in routes
            if isinstance(route, dict) and nonempty_string(route.get("id"))
        }
        result = validate_consultation(
            document.get("notebooklm_consultation") if isinstance(document, dict) else None,
            path.parent,
            route_ids,
        )
        result.update({"schema": "notebooklm-evidence-receipt-guard/1.0", "decision": str(path)})
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None), flush=True)
        return 0 if result["valid"] else 1
    except (OSError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "schema": "notebooklm-evidence-receipt-guard/1.0",
                    "valid": False,
                    "errors": [f"{type(exc).__name__}: {exc}"],
                },
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            ),
            flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
