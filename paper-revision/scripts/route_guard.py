#!/usr/bin/env python3
"""Validate a bounded route-selection decision for paper revision.

Stdlib-only so it can run in the same supported Python environments.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from notebooklm_receipt_guard import CONSULTATION_STATES, ROLES, validate_consultation


ROUTE_TYPES = {
    "CLAIM_CALIBRATION",
    "THEORY_REPAIR",
    "EVIDENCE_REPAIR",
    "SCOPE_REMOVAL",
    "EVIDENCE_REBUTTAL",
    "HUMAN_DECISION",
}
ROUTE_DECISIONS = {"RECOMMENDED", "VIABLE", "REJECTED", "NEEDS_HUMAN_DECISION"}
SELECTION_STATES = {
    "AWAITING_USER_APPROVAL",
    "SELECTED",
    "NEEDS_HUMAN_DECISION",
    "BLOCKED",
    "SKIPPED",
}
USER_DECISION_STATES = {"PENDING", "APPROVED", "NOT_REQUIRED"}
OUTCOMES = {"PASS", "PARTIAL", "FAIL", "NOT_APPLICABLE", "UNVERIFIABLE"}
CRITERIA = tuple(f"RG{number}" for number in range(1, 10))
HARD_GATES = {"RG1", "RG2", "RG3", "RG7"}


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: Any, *, allow_empty: bool = True) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(nonempty_string(item) for item in value)
    )


def validate_route(route: Any, index: int, errors: list[str]) -> tuple[str | None, str | None]:
    prefix = f"routes[{index}]"
    if not isinstance(route, dict):
        errors.append(f"{prefix}: must be an object.")
        return None, None

    route_id = route.get("id")
    if not nonempty_string(route_id) or not re.fullmatch(r"R-[A-Z0-9]+", route_id.strip()):
        errors.append(f"{prefix}: id must look like R-A or R-2.")
        route_id = None
    else:
        route_id = route_id.strip()

    route_type = route.get("type")
    if route_type not in ROUTE_TYPES:
        errors.append(f"{prefix}: type must be one of {sorted(ROUTE_TYPES)}.")

    decision = route.get("decision")
    if decision not in ROUTE_DECISIONS:
        errors.append(f"{prefix}: decision must be one of {sorted(ROUTE_DECISIONS)}.")
        decision = None

    if not nonempty_string(route.get("proposal")):
        errors.append(f"{prefix}: proposal is required.")

    for field, allow_empty in (
        ("existing_evidence", True),
        ("new_evidence_required", True),
        ("applicable_paper_rubric_layers", True),
        ("ripple_targets", True),
        ("verification_checks", False),
    ):
        if not string_list(route.get(field), allow_empty=allow_empty):
            qualifier = "" if allow_empty else " non-empty"
            errors.append(f"{prefix}.{field}: must be a{qualifier} array of strings.")

    layers = route.get("applicable_paper_rubric_layers", [])
    if isinstance(layers, list):
        for layer in layers:
            if nonempty_string(layer) and not re.fullmatch(r"L(?:10|[0-9])(?:[.][A-Za-z0-9_-]+)?", layer.strip()):
                errors.append(f"{prefix}.applicable_paper_rubric_layers: {layer!r} is invalid.")

    findings = route.get("findings")
    outcomes: dict[str, str] = {}
    if not isinstance(findings, list):
        errors.append(f"{prefix}.findings: must be an array containing RG1 through RG9.")
    else:
        for finding_index, finding in enumerate(findings, 1):
            finding_prefix = f"{prefix}.findings[{finding_index}]"
            if not isinstance(finding, dict):
                errors.append(f"{finding_prefix}: must be an object.")
                continue
            criterion_id = finding.get("criterion_id")
            if criterion_id not in CRITERIA:
                errors.append(f"{finding_prefix}: criterion_id must be one of {list(CRITERIA)}.")
                continue
            if criterion_id in outcomes:
                errors.append(f"{finding_prefix}: duplicate criterion {criterion_id}.")
            outcome = finding.get("outcome")
            if outcome not in OUTCOMES:
                errors.append(f"{finding_prefix}: outcome must be one of {sorted(OUTCOMES)}.")
            else:
                outcomes[criterion_id] = outcome
            if not nonempty_string(finding.get("evidence")):
                errors.append(f"{finding_prefix}: evidence is required.")

        missing = [criterion for criterion in CRITERIA if criterion not in outcomes]
        if missing:
            errors.append(f"{prefix}.findings: missing criteria {', '.join(missing)}.")

    if decision in {"RECOMMENDED", "VIABLE"}:
        failed_hard_gates = [
            criterion for criterion in sorted(HARD_GATES) if outcomes.get(criterion) != "PASS"
        ]
        if failed_hard_gates:
            errors.append(
                f"{prefix}: {decision} requires PASS on hard gates; non-passing: "
                f"{', '.join(failed_hard_gates)}."
            )

    return route_id, decision


def validate_user_route_decision(
    value: Any,
    errors: list[str],
) -> tuple[str | None, str | None]:
    prefix = "user_route_decision"
    if not isinstance(value, dict):
        errors.append(f"{prefix}: must be an object.")
        return None, None

    status = value.get("status")
    if status not in USER_DECISION_STATES:
        errors.append(f"{prefix}.status must be one of {sorted(USER_DECISION_STATES)}.")
        status = None

    route_id = value.get("route_id")
    if route_id is not None and (
        not nonempty_string(route_id)
        or not re.fullmatch(r"R-[A-Z0-9]+", route_id.strip())
    ):
        errors.append(f"{prefix}.route_id must be null or look like R-A.")
        route_id = None
    elif isinstance(route_id, str):
        route_id = route_id.strip()

    evidence = value.get("evidence")
    if status == "APPROVED":
        if route_id is None:
            errors.append(f"{prefix}: APPROVED requires route_id.")
        if not nonempty_string(evidence):
            errors.append(
                f"{prefix}: APPROVED requires the user's explicit post-presentation response."
            )
    elif status in {"PENDING", "NOT_REQUIRED"}:
        if route_id is not None:
            errors.append(f"{prefix}: {status} requires route_id=null.")
        if evidence is not None:
            errors.append(f"{prefix}: {status} requires evidence=null.")

    return status, route_id


def validate_context_envelope(value: Any, errors: list[str]) -> None:
    prefix = "context_envelope"
    if not isinstance(value, dict):
        errors.append(f"{prefix}: must be an object when the route gate applies.")
        return
    for field in (
        "target_scope",
        "preceding_context",
        "following_context",
        "abstraction_contract",
    ):
        if not nonempty_string(value.get(field)):
            errors.append(f"{prefix}.{field} is required.")
    for field, allow_empty in (
        ("definitions_and_symbols_checked", True),
        ("downstream_occurrences_checked", True),
        ("protected_anchors", True),
    ):
        if not string_list(value.get(field), allow_empty=allow_empty):
            qualifier = "" if allow_empty else " non-empty"
            errors.append(f"{prefix}.{field} must be a{qualifier} array of strings.")

    reviewer_census = value.get("reviewer_census")
    if not isinstance(reviewer_census, dict):
        errors.append(f"{prefix}.reviewer_census must be an object.")
    else:
        for field in (
            "direct_comment_ids",
            "inherited_ripple_ids",
            "adjacent_block_comment_ids",
            "internal_defect_ids",
        ):
            if not string_list(reviewer_census.get(field), allow_empty=True):
                errors.append(f"{prefix}.reviewer_census.{field} must be an array of strings.")
        reviewer_id_fields = (
            "direct_comment_ids",
            "inherited_ripple_ids",
            "adjacent_block_comment_ids",
        )
        assigned: dict[str, str] = {}
        for field in reviewer_id_fields:
            values = reviewer_census.get(field, [])
            if isinstance(values, list):
                for reviewer_id in values:
                    if not nonempty_string(reviewer_id):
                        continue
                    if not re.fullmatch(r"(?:R|C)[1-9][0-9]*", reviewer_id.strip()):
                        errors.append(
                            f"{prefix}.reviewer_census.{field}: {reviewer_id!r} is not a reviewer ID."
                        )
                    if reviewer_id in assigned:
                        errors.append(
                            f"{prefix}.reviewer_census: {reviewer_id} appears in both "
                            f"{assigned[reviewer_id]} and {field}."
                        )
                    else:
                        assigned[reviewer_id] = field
        if not string_list(reviewer_census.get("evidence_anchors"), allow_empty=False):
            errors.append(
                f"{prefix}.reviewer_census.evidence_anchors must be a non-empty array of strings."
            )
        if not nonempty_string(reviewer_census.get("bounded_conclusion")):
            errors.append(f"{prefix}.reviewer_census.bounded_conclusion is required.")


def consultation_declaration(
    value: Any,
    errors: list[str],
) -> tuple[str | None, list[str], list[str]]:
    prefix = "notebooklm_consultation"
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be an object.")
        return None, [], []
    status = value.get("status")
    if status not in CONSULTATION_STATES:
        errors.append(f"{prefix}.status must be one of {sorted(CONSULTATION_STATES)}.")
    required_roles = value.get("required_roles")
    if not string_list(required_roles, allow_empty=True):
        errors.append(f"{prefix}.required_roles must be an array of strings.")
        required_roles = []
    invalid_roles = sorted(set(required_roles) - ROLES)
    if invalid_roles:
        errors.append(f"{prefix}.required_roles contains invalid roles: {', '.join(invalid_roles)}.")
    receipts = value.get("receipts")
    if not isinstance(receipts, list):
        errors.append(f"{prefix}.receipts must be an array.")
        receipts = []
    query_ids = [
        item.get("query_id")
        for item in receipts
        if isinstance(item, dict) and nonempty_string(item.get("query_id"))
    ]
    return status, required_roles, query_ids


def validate_document(document: Any, evidence_base_dir: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(document, dict):
        return {"valid": False, "errors": ["Document root must be a JSON object."], "warnings": []}

    if document.get("schema_version") != 1:
        errors.append("schema_version must be 1.")
    if not nonempty_string(document.get("task_id")):
        errors.append("task_id is required.")
    gate_required = document.get("gate_required")
    if not isinstance(gate_required, bool):
        errors.append("gate_required must be a boolean.")
    if not nonempty_string(document.get("gate_reason")):
        errors.append("gate_reason is required.")
    if gate_required is True:
        validate_context_envelope(document.get("context_envelope"), errors)
    elif document.get("context_envelope") is not None:
        errors.append("context_envelope must be null when the route gate is skipped.")

    rounds = document.get("route_rounds")
    if isinstance(rounds, bool) or not isinstance(rounds, int) or not 0 <= rounds <= 2:
        errors.append("route_rounds must be an integer from 0 to 2.")

    selection_state = document.get("selection_state")
    if selection_state not in SELECTION_STATES:
        errors.append(f"selection_state must be one of {sorted(SELECTION_STATES)}.")

    selected_route_id = document.get("selected_route_id")
    if selected_route_id is not None and (
        not nonempty_string(selected_route_id)
        or not re.fullmatch(r"R-[A-Z0-9]+", selected_route_id.strip())
    ):
        errors.append("selected_route_id must be null or look like R-A.")

    if not nonempty_string(document.get("selection_basis")):
        errors.append("selection_basis is required.")
    if not string_list(document.get("notebooklm_query_ids"), allow_empty=True):
        errors.append("notebooklm_query_ids must be an array of strings.")
    declared_query_ids = document.get("notebooklm_query_ids", [])

    user_decision_status, user_decision_route_id = validate_user_route_decision(
        document.get("user_route_decision"),
        errors,
    )

    routes = document.get("routes")
    route_pairs: list[tuple[str | None, str | None]] = []
    if not isinstance(routes, list):
        errors.append("routes must be an array.")
        routes = []
    else:
        for index, route in enumerate(routes, 1):
            route_pairs.append(validate_route(route, index, errors))
        if len(routes) > 3:
            errors.append("routes may contain at most three genuinely distinct strategies.")

    route_ids = [route_id for route_id, _ in route_pairs if route_id]
    duplicates = sorted({route_id for route_id in route_ids if route_ids.count(route_id) > 1})
    if duplicates:
        errors.append(f"Duplicate route IDs: {', '.join(duplicates)}.")

    consultation_status, required_roles, receipt_query_ids = consultation_declaration(
        document.get("notebooklm_consultation"),
        errors,
    )
    receipt_result: dict[str, Any] | None = None
    # Local scientific blockers need no external receipt, but their NOT_REQUIRED
    # declaration must still pass every consultation check in structure-only use.
    local_blocked = selection_state == "BLOCKED" and consultation_status == "NOT_REQUIRED"
    if evidence_base_dir is not None or local_blocked:
        receipt_result = validate_consultation(
            document.get("notebooklm_consultation"),
            evidence_base_dir if evidence_base_dir is not None else Path.cwd(),
            set(route_ids),
        )
        errors.extend(receipt_result["errors"])
        receipt_query_ids = receipt_result["verified_query_ids"]
    if sorted(declared_query_ids) != sorted(receipt_query_ids):
        errors.append(
            "notebooklm_query_ids must match the query IDs backed by evidence receipts."
        )

    recommended = [route_id for route_id, decision in route_pairs if decision == "RECOMMENDED"]
    viable = [route_id for route_id, decision in route_pairs if decision == "VIABLE"]
    if len(recommended) > 1:
        errors.append("At most one route may be RECOMMENDED.")

    if selection_state == "SKIPPED":
        if gate_required is not False:
            errors.append("SKIPPED requires gate_required=false.")
        if rounds != 0:
            errors.append("SKIPPED requires route_rounds=0.")
        if routes:
            errors.append("SKIPPED requires an empty routes array.")
        if selected_route_id is not None:
            errors.append("SKIPPED requires selected_route_id=null.")
        if user_decision_status != "NOT_REQUIRED":
            errors.append("SKIPPED requires user_route_decision.status=NOT_REQUIRED.")
        if consultation_status != "NOT_REQUIRED":
            errors.append("SKIPPED requires notebooklm_consultation.status=NOT_REQUIRED.")
    else:
        if gate_required is not True:
            errors.append(f"{selection_state} requires gate_required=true.")
        if not isinstance(rounds, int) or isinstance(rounds, bool) or rounds not in {1, 2}:
            errors.append(f"{selection_state} requires route_rounds of 1 or 2.")
        if not routes:
            errors.append(f"{selection_state} requires at least one route.")

    if selection_state == "AWAITING_USER_APPROVAL":
        if selected_route_id is not None:
            errors.append("AWAITING_USER_APPROVAL requires selected_route_id=null.")
        if user_decision_status != "PENDING":
            errors.append(
                "AWAITING_USER_APPROVAL requires user_route_decision.status=PENDING."
            )
        if not recommended and not viable:
            errors.append(
                "AWAITING_USER_APPROVAL requires at least one RECOMMENDED or VIABLE route."
            )
        if consultation_status not in {"COMPLETED", "NOT_REQUIRED"}:
            errors.append(
                "AWAITING_USER_APPROVAL requires verified consultation or a justified NOT_REQUIRED local evaluation."
            )
    elif selection_state == "SELECTED":
        if not nonempty_string(selected_route_id):
            errors.append("SELECTED requires selected_route_id.")
        elif selected_route_id not in route_ids:
            errors.append("selected_route_id is not present in routes.")
        elif selected_route_id not in recommended + viable:
            errors.append("SELECTED route must be RECOMMENDED or VIABLE.")
        if user_decision_status != "APPROVED":
            errors.append("SELECTED requires user_route_decision.status=APPROVED.")
        if user_decision_route_id != selected_route_id:
            errors.append(
                "user_route_decision.route_id must match selected_route_id."
            )
        if consultation_status not in {"COMPLETED", "NOT_REQUIRED"}:
            errors.append("SELECTED requires verified consultation or a justified NOT_REQUIRED local evaluation.")
    elif selection_state in {"NEEDS_HUMAN_DECISION", "BLOCKED"}:
        if selected_route_id is not None:
            errors.append(f"{selection_state} requires selected_route_id=null.")
        if recommended:
            errors.append(f"{selection_state} cannot contain a RECOMMENDED route.")
        if selection_state == "NEEDS_HUMAN_DECISION" and not any(
            decision == "NEEDS_HUMAN_DECISION" for _, decision in route_pairs
        ) and len(viable) < 2:
            errors.append(
                "NEEDS_HUMAN_DECISION requires one route marked NEEDS_HUMAN_DECISION or at least two VIABLE routes."
            )
        if selection_state == "BLOCKED" and viable:
            errors.append("BLOCKED cannot contain a VIABLE route.")
        expected_user_status = (
            "PENDING" if selection_state == "NEEDS_HUMAN_DECISION" else "NOT_REQUIRED"
        )
        if user_decision_status != expected_user_status:
            errors.append(
                f"{selection_state} requires user_route_decision.status={expected_user_status}."
            )
        if selection_state == "BLOCKED" and consultation_status not in {
            "BLOCKED",
            "COMPLETED",
            "NOT_REQUIRED",
        }:
            errors.append(
                "BLOCKED route selection requires a blocked/completed consultation "
                "or a justified NOT_REQUIRED local evaluation."
            )
        if selection_state == "NEEDS_HUMAN_DECISION" and consultation_status not in {
            "COMPLETED", "NOT_REQUIRED"
        }:
            errors.append(
                "NEEDS_HUMAN_DECISION requires verified consultation or a justified NOT_REQUIRED local evaluation."
            )

    return {
        "valid": not errors,
        "selection_state": selection_state,
        "route_count": len(routes),
        "selected_route_id": selected_route_id,
        "consultation_status": consultation_status,
        "verified_notebooklm_query_ids": receipt_query_ids,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a paper-revision route decision")
    parser.add_argument("decision", help="Path to route-decision.json")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    try:
        path = Path(args.decision).expanduser().resolve()
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        result = validate_document(document, path.parent)
        result.update({"schema": "route-selection-guard/1.0", "decision": str(path)})
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None), flush=True)
        return 0 if result["valid"] else 1
    except (OSError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "schema": "route-selection-guard/1.0",
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
