#!/usr/bin/env python3
"""Validate recorded human approvals and the exact manuscript candidate.

The guard is intentionally stdlib-only for the supported Python environments.
It does not edit the manuscript; it only returns READY_TO_APPLY or BLOCKED.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from notebooklm_receipt_guard import normalize_candidate_text, validate_candidate_consultation
from route_guard import validate_document as validate_route_document


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate(state: Any, state_path: Path, candidate_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    preview_after: str | None = None
    if not isinstance(state, dict):
        return {"ready": False, "state": "BLOCKED", "errors": ["State root must be an object."]}

    if state.get("schema_version") != 1:
        errors.append("schema_version must be 1.")
    if not nonempty_string(state.get("task_id")):
        errors.append("task_id is required.")

    selected_route_id = state.get("selected_route_id")
    if selected_route_id is not None and (
        not nonempty_string(selected_route_id)
        or not re.fullmatch(r"R-[A-Z0-9]+", selected_route_id.strip())
    ):
        errors.append("selected_route_id must be null or look like R-A.")
    elif isinstance(selected_route_id, str):
        selected_route_id = selected_route_id.strip()

    route_file_value = state.get("route_decision_file")
    route_document: Any = None
    route_path: Path | None = None
    if not nonempty_string(route_file_value):
        errors.append("route_decision_file is required.")
    else:
        route_path = Path(route_file_value).expanduser()
        if not route_path.is_absolute():
            route_path = state_path.parent / route_path
        try:
            route_document = read_json(route_path.resolve())
            if not isinstance(route_document, dict):
                errors.append("route_decision_file must contain a JSON object.")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Could not read route_decision_file: {type(exc).__name__}: {exc}")

    if isinstance(route_document, dict):
        route_validation = validate_route_document(route_document, route_path.resolve().parent)
        if not route_validation["valid"]:
            errors.append(
                "Route decision or its NotebookLM evidence receipts are invalid: "
                + " | ".join(route_validation["errors"])
            )
        if route_document.get("task_id") != state.get("task_id"):
            errors.append("Route decision task_id does not match this approval state.")
        route_state = route_document.get("selection_state")
        if route_state not in {"SELECTED", "SKIPPED"}:
            errors.append("Route decision must have selection_state=SELECTED or SKIPPED.")
        if route_document.get("selected_route_id") != selected_route_id:
            errors.append("Route decision selected_route_id does not match this state.")
        user_route = route_document.get("user_route_decision")
        if route_state == "SELECTED":
            if not nonempty_string(selected_route_id):
                errors.append("A selected route requires a non-empty selected_route_id.")
            if not isinstance(user_route, dict) or user_route.get("status") != "APPROVED":
                errors.append("Route decision lacks explicit user route approval.")
            elif user_route.get("route_id") != selected_route_id:
                errors.append("Approved user route does not match selected_route_id.")
            elif not nonempty_string(user_route.get("evidence")):
                errors.append("Route approval evidence is empty.")
        elif route_state == "SKIPPED" and selected_route_id is not None:
            errors.append("A skipped route gate requires selected_route_id=null.")

    preview = state.get("chat_preview")
    if not isinstance(preview, dict):
        errors.append("chat_preview must be an object.")
    else:
        if preview.get("shown_to_user") is not True:
            errors.append("The exact candidate must be shown to the user before approval.")
        preview_format = preview.get("format")
        if preview_format != "EXACT_LATEX":
            errors.append("chat_preview.format must be EXACT_LATEX.")
        if not nonempty_string(preview.get("after")):
            errors.append("chat_preview.after is required.")
        else:
            preview_after = preview["after"]
        has_reason = nonempty_string(preview.get("reason"))
        has_main_changes = (
            isinstance(preview.get("main_changes"), list)
            and bool(preview.get("main_changes"))
            and all(nonempty_string(item) for item in preview.get("main_changes"))
        )
        if not has_reason and not has_main_changes:
            errors.append("chat_preview.reason or chat_preview.main_changes is required.")

    try:
        actual_candidate_sha256 = sha256_file(candidate_path.resolve())
        actual_candidate_text = candidate_path.resolve().read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        errors.append(f"Could not read candidate file: {type(exc).__name__}: {exc}")
        actual_candidate_sha256 = None
        actual_candidate_text = None

    if preview_after is not None and actual_candidate_text is not None:
        if normalize_candidate_text(preview_after) != normalize_candidate_text(
            actual_candidate_text
        ):
            errors.append(
                "chat_preview.after does not match the exact candidate file shown for approval."
            )

    declared_candidate_sha256 = state.get("candidate_sha256")
    if not isinstance(declared_candidate_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", declared_candidate_sha256
    ):
        errors.append("candidate_sha256 must be a lowercase SHA-256 digest.")
    elif actual_candidate_sha256 != declared_candidate_sha256:
        errors.append("Candidate file changed after the preview was recorded.")

    expected_candidate_roles: set[str] = set()
    if isinstance(route_document, dict):
        route_consultation = route_document.get("notebooklm_consultation")
        if isinstance(route_consultation, dict):
            roles = route_consultation.get("required_roles")
            if isinstance(roles, list):
                expected_candidate_roles = {
                    role for role in roles if role in {"theory", "writing"}
                }
    candidate_consultation_result = validate_candidate_consultation(
        state.get("candidate_notebooklm_consultation"),
        state_path.parent,
        actual_candidate_sha256 or "",
        expected_candidate_roles,
        candidate_text=actual_candidate_text,
    )
    if not candidate_consultation_result["valid"]:
        errors.append(
            "Candidate NotebookLM evidence is invalid: "
            + " | ".join(candidate_consultation_result["errors"])
        )
    draft_audit_query_ids = state.get("draft_audit_query_ids")
    if not isinstance(draft_audit_query_ids, list) or not all(
        nonempty_string(item) for item in draft_audit_query_ids
    ):
        errors.append("draft_audit_query_ids must be an array of strings.")
    elif sorted(draft_audit_query_ids) != sorted(
        candidate_consultation_result["verified_query_ids"]
    ):
        errors.append(
            "draft_audit_query_ids must match the verified candidate receipt query IDs."
        )

    user_draft = state.get("user_draft_decision")
    if not isinstance(user_draft, dict):
        errors.append("user_draft_decision must be an object.")
    else:
        if user_draft.get("status") != "APPROVED":
            errors.append("user_draft_decision.status must be APPROVED.")
        if user_draft.get("candidate_sha256") != declared_candidate_sha256:
            errors.append("Draft approval does not identify the exact candidate digest.")
        if not nonempty_string(user_draft.get("evidence")):
            errors.append(
                "Draft approval requires the user's explicit response after the candidate preview."
            )

    return {
        "ready": not errors,
        "state": "READY_TO_APPLY" if not errors else "BLOCKED",
        "task_id": state.get("task_id"),
        "selected_route_id": selected_route_id,
        "candidate_sha256": actual_candidate_sha256,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate route and draft approval for an exact manuscript candidate"
    )
    parser.add_argument("state", help="Path to manuscript-approval.json")
    parser.add_argument("--candidate", required=True, help="Exact candidate patch or fragment")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    try:
        state_path = Path(args.state).expanduser().resolve()
        state = read_json(state_path)
        result = validate(state, state_path, Path(args.candidate))
        result.update(
            {
                "schema": "manuscript-approval-guard/1.0",
                "approval_state": str(state_path),
            }
        )
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None), flush=True)
        return 0 if result["ready"] else 1
    except (OSError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "schema": "manuscript-approval-guard/1.0",
                    "ready": False,
                    "state": "BLOCKED",
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
