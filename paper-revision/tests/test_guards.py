"""Offline regression tests. All NotebookLM answers here are synthetic fixtures."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import latex_log_summary as logs
import manuscript_approval_guard as approval
import notebooklm_receipt_guard as receipts
import revision_guard as ledger
import route_guard as routes
import writing_source_router as router


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def skipped_route() -> dict:
    return {
        "schema_version": 1, "task_id": "editorial", "gate_required": False,
        "gate_reason": "Deterministic verified typo.", "context_envelope": None,
        "route_rounds": 0, "selection_state": "SKIPPED", "selected_route_id": None,
        "selection_basis": "Known typo with no semantic change.", "notebooklm_query_ids": [],
        "notebooklm_consultation": {
            "status": "NOT_REQUIRED", "required_roles": [], "reason": "Literal typo.",
            "receipts": [], "findings": [],
        },
        "user_route_decision": {"status": "NOT_REQUIRED", "route_id": None, "evidence": None},
        "routes": [],
    }


def local_scientific_blocked_route() -> dict:
    document = json.loads((ROOT / "references/route-decision.example.json").read_text())
    document.update(
        task_id="editorial", selection_state="BLOCKED", selected_route_id=None,
        gate_reason="The requested formal guarantee has no inspected proof.",
        selection_basis="Nominal simulation evidence cannot establish the requested universal guarantee.",
        notebooklm_query_ids=[],
        user_route_decision={"status": "NOT_REQUIRED", "route_id": None, "evidence": None},
        notebooklm_consultation={
            "status": "NOT_REQUIRED", "required_roles": [],
            "reason": "Local evidence establishes the missing proof; no project or user policy requires a notebook consultation.",
            "receipts": [], "findings": [],
        },
    )
    route = document["routes"][0]
    route["decision"] = "REJECTED"
    route["proposal"] = "Add the requested universal stability guarantee."
    route["new_evidence_required"] = ["An applicable formal statement, its assumptions and a checked proof."]
    for finding in route["findings"]:
        if finding["criterion_id"] in {"RG2", "RG6"}:
            finding.update(outcome="UNVERIFIABLE", evidence="The inspected local results contain no stability proof.")
    return document


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.text = "The measured residual is denoted by $r(t)$.\n"
        self.candidate = self.base / "candidate.tex"
        self.candidate.write_text(self.text, encoding="utf-8")
        self.sha = digest(self.candidate.read_bytes())

    def prompt(self, text=None, sha=None):
        return (
            "TASK_ID: editorial-final-writing-r1\nROLE: Scientific-writing auditor.\n"
            f"CANDIDATE_SHA256: {sha or self.sha}\n"
            "REVISED_TEXT_BEGIN\n" + (self.text if text is None else text)
            + "REVISED_TEXT_END\nOUTPUT_SCHEMA:\n"
            "VERDICT: [PASS | FAIL | INSUFFICIENT_EVIDENCE]\n"
            "FAILED_CRITERIA: [items or NONE]\nEVIDENCE: [source markers]\n"
            "REQUIRED_CHANGE: [correction or NONE]\n"
        )

    def consultation(self, *, answer=None, prompt=None, partial=False):
        question = self.prompt() if prompt is None else prompt
        prompt_path = self.base / "query.txt"
        # Preserve supplied CRLF exactly; Windows text writes would turn it into CRCRLF.
        prompt_path.write_bytes(question.encode("utf-8"))
        answer = answer or (
            "VERDICT: PASS\nFAILED_CRITERIA: NONE\n"
            "EVIDENCE: [1] supports the grammatical equation integration.\nREQUIRED_CHANGE: NONE\n"
        )
        result = {
            "query_id": "editorial-final-writing-r1", "status": "success",
            "notebook_id": "synthetic-writing", "retrieval_method": "direct_cli",
            "request": {"question_sha256": digest(prompt_path.read_text(encoding="utf-8-sig").strip().encode()), "source_ids": ["synthetic-source"]},
            "answer": answer, "references": [],
        }
        payload = {
            "schema": "notebooklm-agent-wrapper/2.5.2", "status": "partial" if partial else "success",
            "command": "batch" if partial else "ask",
        }
        if partial:
            payload["results"] = [result, {"query_id": "other", "status": "error"}]
        else:
            payload["result"] = result
        output = self.base / "query.json"
        output.write_text(json.dumps(payload), encoding="utf-8")
        return {
            "status": "COMPLETED", "required_roles": ["writing"], "candidate_sha256": self.sha,
            "reason": "Synthetic writing audit.",
            "receipts": [{
                "query_id": result["query_id"], "role": "writing", "notebook_id": result["notebook_id"],
                "source_ids": ["synthetic-source"], "prompt_file": str(prompt_path),
                "output_file": str(output), "output_sha256": digest(output.read_bytes()),
            }],
            "findings": [{"query_id": result["query_id"], "role": "writing", "verdict": "PASS", "evidence": "[1]"}],
        }

    def validate_consultation(self, **kwargs):
        consultation = self.consultation(**kwargs)
        return receipts.validate_candidate_consultation(
            consultation, self.base, self.sha, {"writing"}, candidate_text=self.text
        )

    def editorial_state(self):
        route_path = self.base / "route.json"
        route_path.write_text(json.dumps(skipped_route()), encoding="utf-8")
        return {
            "schema_version": 1, "task_id": "editorial", "route_decision_file": "route.json",
            "selected_route_id": None, "candidate_sha256": self.sha,
            "chat_preview": {"shown_to_user": True, "format": "EXACT_LATEX", "after": self.text, "reason": "Typo."},
            "candidate_notebooklm_consultation": {
                "status": "NOT_REQUIRED", "required_roles": [], "candidate_sha256": self.sha,
                "reason": "Literal repair.", "receipts": [], "findings": [],
            },
            "draft_audit_query_ids": [],
            "user_draft_decision": {"status": "APPROVED", "candidate_sha256": self.sha, "evidence": "Apply this version."},
        }

    def test_bundled_route_receipts(self):
        document = json.loads((ROOT / "references/route-decision.example.json").read_text())
        result = routes.validate_document(document, ROOT / "references")
        self.assertTrue(result["valid"], result["errors"])

    def test_wrong_route_receipt_digest_rejected(self):
        document = json.loads((ROOT / "references/route-decision.example.json").read_text())
        document["notebooklm_consultation"]["receipts"][0]["output_sha256"] = "0" * 64
        self.assertFalse(routes.validate_document(document, ROOT / "references")["valid"])

    def test_reviewer_ids_do_not_become_legacy_routes(self):
        prompt = (ROOT / "references/receipt-examples/C1-theory-route-r1.txt").read_text()
        prompt += "\nINHERITED_REVIEWER_IDS: R8, R1\n"
        self.assertEqual([], receipts.validate_prompt_neutrality(prompt, phase="route", role="theory", route_ids={"R-A"}))

    def test_legacy_route_header_rejected(self):
        prompt = "CANDIDATE_ROUTES:\nR1 | THEORY_REPAIR | repair\nEVALUATE: RG2 RG3 RG6 RG7\n"
        self.assertTrue(receipts.validate_prompt_neutrality(prompt, phase="route", role="theory", route_ids={"R1"}))

    def test_preferred_route_is_rejected(self):
        prompt = "CANDIDATE_ROUTES:\nR-A | recommended repair\nEVALUATE: RG2 RG3 RG6 RG7\n"
        self.assertTrue(receipts.validate_prompt_neutrality(prompt, phase="route", role="theory", route_ids={"R-A"}))

    def test_candidate_output_vocabulary_allowed(self):
        prompt = self.prompt().replace("[PASS | FAIL | INSUFFICIENT_EVIDENCE]", "PASS | FAIL | INSUFFICIENT_EVIDENCE")
        self.assertEqual([], receipts.validate_prompt_neutrality(prompt, phase="candidate", role="writing", route_ids=set()))

    def test_seeded_candidate_verdict_rejected(self):
        prompt = self.prompt().replace("[PASS | FAIL | INSUFFICIENT_EVIDENCE]", "PASS")
        self.assertTrue(receipts.validate_prompt_neutrality(prompt, phase="candidate", role="writing", route_ids=set()))

    def test_candidate_requires_literal_block_and_digest(self):
        self.assertTrue(receipts.validate_prompt_neutrality("VERDICT: [PASS | FAIL]", phase="candidate", role="writing", route_ids=set()))

    def test_shipped_candidate_templates_pass_preflight(self):
        pack = (ROOT / "references/notebooklm-prompts.md").read_text()
        for role in ("Theory", "Writing"):
            prompt = pack.split(f"### {role} candidate")[1].split("```text", 1)[1].split("```", 1)[0]
            prompt = prompt.replace("[task]", "T1").replace("[round]", "1")
            prompt = prompt.replace("[64 lowercase hexadecimal characters]", self.sha)
            prompt = prompt.replace("[exact LaTeX candidate]", self.text.rstrip("\n"))
            errors = receipts.validate_prompt_neutrality(prompt, phase="candidate", role=role.lower(), route_ids=set())
            self.assertEqual([], errors, role)

    def test_shipped_route_templates_pass_preflight(self):
        pack = (ROOT / "references/notebooklm-prompts.md").read_text()
        for role in ("Theory", "Writing"):
            prompt = pack.split(f"### {role} route")[1].split("```text", 1)[1].split("```", 1)[0]
            prompt = prompt.replace("[task]", "T1").replace("[round]", "1")
            errors = receipts.validate_prompt_neutrality(prompt, phase="route", role=role.lower(), route_ids={"R-A", "R-B"})
            self.assertEqual([], errors, role)

    def test_exact_candidate_receipt_accepted(self):
        result = self.validate_consultation()
        self.assertTrue(result["valid"], result["errors"])

    def test_wrong_candidate_with_same_digest_rejected(self):
        self.assertFalse(self.validate_consultation(prompt=self.prompt(text="Different text.\n"))["valid"])

    def test_wrong_digest_with_same_candidate_rejected(self):
        self.assertFalse(self.validate_consultation(prompt=self.prompt(sha="0" * 64))["valid"])

    def test_duplicate_candidate_blocks_rejected(self):
        prompt = self.prompt() + "REVISED_TEXT_BEGIN\nExtra.\nREVISED_TEXT_END\n"
        self.assertFalse(self.validate_consultation(prompt=prompt)["valid"])

    def test_line_ending_normalization(self):
        self.text = "The measured residual is denoted by $r(t)$.\n\nIts norm is reported separately.\n"
        for candidate_ending in ("\n", "\r\n"):
            self.candidate.write_bytes(self.text.replace("\n", candidate_ending).encode("utf-8"))
            self.sha = digest(self.candidate.read_bytes())
            for prompt_ending in ("\n", "\r\n"):
                with self.subTest(candidate_ending=candidate_ending, prompt_ending=prompt_ending):
                    question = self.prompt().replace("\n", prompt_ending)
                    result = self.validate_consultation(prompt=question)
                    self.assertEqual(question.encode("utf-8"), (self.base / "query.txt").read_bytes())
                    self.assertTrue(result["valid"], result["errors"])

    def test_changed_internal_blank_lines_rejected(self):
        self.text = "The measured residual is denoted by $r(t)$.\nIts norm is reported separately.\n"
        self.candidate.write_bytes(self.text.encode("utf-8"))
        self.sha = digest(self.candidate.read_bytes())
        changed_text = self.text.replace("\n", "\n\n", 1)
        result = self.validate_consultation(prompt=self.prompt(text=changed_text))
        self.assertFalse(result["valid"])
        self.assertTrue(any("literal REVISED_TEXT block does not match" in error for error in result["errors"]))

    def test_line_ending_change_requires_new_candidate_digest(self):
        self.candidate.write_bytes(self.text.encode("utf-8"))
        self.sha = digest(self.candidate.read_bytes())
        state = self.editorial_state()
        self.candidate.write_bytes(self.text.replace("\n", "\r\n").encode("utf-8"))
        result = approval.validate(state, self.base / "approval.json", self.candidate)
        self.assertFalse(result["ready"])
        self.assertTrue(any("candidate_sha256" in error for error in result["errors"]))

    def test_empty_evidence_rejected(self):
        answer = "VERDICT: PASS\nFAILED_CRITERIA: NONE\nEVIDENCE: NONE\nREQUIRED_CHANGE: NONE"
        self.assertFalse(self.validate_consultation(answer=answer)["valid"])

    def test_duplicate_verdicts_rejected(self):
        answer = "VERDICT: PASS\nFAILED_CRITERIA: NONE\nEVIDENCE: [1]\nREQUIRED_CHANGE: NONE\nVERDICT: FAIL"
        self.assertFalse(self.validate_consultation(answer=answer)["valid"])

    def test_pass_with_failed_criterion_rejected(self):
        answer = "VERDICT: PASS\nFAILED_CRITERIA: EW5 undefined symbol\nEVIDENCE: [1]\nREQUIRED_CHANGE: NONE"
        self.assertFalse(self.validate_consultation(answer=answer)["valid"])

    def test_pass_with_required_change_rejected(self):
        answer = "VERDICT: PASS\nFAILED_CRITERIA: NONE\nEVIDENCE: [1]\nREQUIRED_CHANGE: Define the threshold."
        self.assertFalse(self.validate_consultation(answer=answer)["valid"])

    def test_bold_answer_labels_accepted(self):
        answer = "**VERDICT:** PASS\n**FAILED_CRITERIA:** NONE\n**EVIDENCE:** [1] source support\n**REQUIRED_CHANGE:** NONE"
        self.assertTrue(self.validate_consultation(answer=answer)["valid"])

    def test_successful_query_in_partial_batch_accepted(self):
        self.assertTrue(self.validate_consultation(partial=True)["valid"])

    def test_missing_required_expert_blocks_partial_completion(self):
        consultation = self.consultation(partial=True)
        consultation["required_roles"] = ["writing", "theory"]
        result = receipts.validate_candidate_consultation(consultation, self.base, self.sha, {"writing", "theory"}, self.text)
        self.assertFalse(result["valid"])

    def test_skipped_editorial_route_accepted(self):
        self.assertTrue(routes.validate_document(skipped_route(), self.base)["valid"])

    def test_skipped_route_still_requires_draft_approval(self):
        state = self.editorial_state()
        state["user_draft_decision"]["status"] = "PENDING"
        self.assertFalse(approval.validate(state, self.base / "approval.json", self.candidate)["ready"])

    def test_approved_skipped_candidate_ready(self):
        result = approval.validate(self.editorial_state(), self.base / "approval.json", self.candidate)
        self.assertTrue(result["ready"], result["errors"])

    def test_preview_mismatch_rejected(self):
        state = self.editorial_state()
        state["chat_preview"]["after"] = "Different candidate."
        self.assertFalse(approval.validate(state, self.base / "approval.json", self.candidate)["ready"])

    def test_approval_cross_task_link_rejected(self):
        state = self.editorial_state()
        state["task_id"] = "another-task"
        self.assertFalse(approval.validate(state, self.base / "approval.json", self.candidate)["ready"])

    def test_non_object_route_manifest_cannot_bypass_approval(self):
        for value in ([], None, "not a route manifest"):
            state = self.editorial_state()
            (self.base / "route.json").write_text(json.dumps(value))
            self.assertFalse(approval.validate(state, self.base / "approval.json", self.candidate)["ready"])

    def test_candidate_round_three_rejected(self):
        consultation = self.consultation()
        receipt = consultation["receipts"][0]
        receipt["query_id"] = "editorial-final-writing-r3"
        errors = []
        receipts.validate_receipt(receipt, 1, self.base, set(), errors, phase="candidate", candidate_sha256=self.sha, candidate_text=self.text)
        self.assertTrue(any("bounded -r1 or -r2" in error for error in errors))

    def test_local_route_requires_human_route_choice(self):
        document = json.loads((ROOT / "references/route-decision.example.json").read_text())
        document["notebooklm_consultation"] = {
            "status": "NOT_REQUIRED", "required_roles": [], "reason": "Inspected self-contained local evidence.",
            "receipts": [], "findings": [],
        }
        document["notebooklm_query_ids"] = []
        self.assertTrue(routes.validate_document(document, self.base)["valid"])
        document["selection_state"] = "SELECTED"
        document["selected_route_id"] = "R-A"
        self.assertFalse(routes.validate_document(document, self.base)["valid"])
        document["user_route_decision"] = {"status": "APPROVED", "route_id": "R-A", "evidence": "Choose route A."}
        self.assertTrue(routes.validate_document(document, self.base)["valid"])

    def test_local_scientific_blocked_route_accepted(self):
        for evidence_base in (self.base, None):
            with self.subTest(evidence_base=evidence_base):
                result = routes.validate_document(local_scientific_blocked_route(), evidence_base)
                self.assertTrue(result["valid"], result["errors"])
                self.assertEqual([], result["verified_notebooklm_query_ids"])
                self.assertIsNone(result["selected_route_id"])

    def test_local_blocked_cannot_waive_required_roles_or_claim_receipts(self):
        mutations = (
            ("required_roles", ["theory"]),
            ("receipts", [{"query_id": "claimed-theory-route-r1"}]),
            ("findings", [{"query_id": "claimed-theory-route-r1", "outcome": "PASS"}]),
        )
        for evidence_base in (self.base, None):
            for field, value in mutations:
                with self.subTest(evidence_base=evidence_base, field=field):
                    document = local_scientific_blocked_route()
                    document["notebooklm_consultation"][field] = value
                    self.assertFalse(routes.validate_document(document, evidence_base)["valid"])
            document = local_scientific_blocked_route()
            document["notebooklm_query_ids"] = ["claimed-theory-route-r1"]
            self.assertFalse(routes.validate_document(document, evidence_base)["valid"])

    def test_local_blocked_requires_explicit_reason_and_basis(self):
        for evidence_base in (self.base, None):
            for field in ("reason", "selection_basis"):
                with self.subTest(evidence_base=evidence_base, field=field):
                    document = local_scientific_blocked_route()
                    if field == "reason":
                        document["notebooklm_consultation"][field] = ""
                    else:
                        document[field] = ""
                    self.assertFalse(routes.validate_document(document, evidence_base)["valid"])

    def test_local_blocked_cannot_select_or_approve_routes(self):
        for mutation in ("selected_route_id", "approved", "RECOMMENDED", "VIABLE"):
            with self.subTest(mutation=mutation):
                document = local_scientific_blocked_route()
                if mutation == "selected_route_id":
                    document["selected_route_id"] = "R-A"
                elif mutation == "approved":
                    document["user_route_decision"] = {"status": "APPROVED", "route_id": "R-A", "evidence": "Apply it."}
                else:
                    document["routes"][0]["decision"] = mutation
                    # Isolate the BLOCKED-state restriction from hard-gate failures.
                    for finding in document["routes"][0]["findings"]:
                        finding["outcome"] = "PASS"
                self.assertFalse(routes.validate_document(document, self.base)["valid"])

    def test_local_blocked_route_never_authorizes_candidate_application(self):
        state = self.editorial_state()
        (self.base / "route.json").write_text(json.dumps(local_scientific_blocked_route()), encoding="utf-8")
        result = approval.validate(state, self.base / "approval.json", self.candidate)
        self.assertFalse(result["ready"])
        self.assertEqual("BLOCKED", result["state"])
        self.assertIn("Route decision must have selection_state=SELECTED or SKIPPED.", result["errors"])

    def test_new_block_can_have_no_inherited_definitions_or_protected_anchors(self):
        document = json.loads((ROOT / "references/route-decision.example.json").read_text())
        document["context_envelope"]["definitions_and_symbols_checked"] = []
        document["context_envelope"]["protected_anchors"] = []
        document["context_envelope"]["reviewer_census"] = {
            "direct_comment_ids": [], "inherited_ripple_ids": [],
            "adjacent_block_comment_ids": [], "internal_defect_ids": [],
            "evidence_anchors": ["Author objective and inspected source equations."],
            "bounded_conclusion": "Compose task without reviewer comments.",
        }
        result = routes.validate_document(document, ROOT / "references")
        self.assertTrue(result["valid"], result["errors"])

    def test_empty_log_never_passes(self):
        log = self.base / "empty.log"
        log.write_text("")
        self.assertEqual("INCOMPLETE", logs.summarize(log)["status"])
        self.assertEqual("INCOMPLETE", logs.summarize(log, 0)["status"])

    def test_complete_build_passes(self):
        log = self.base / "build.log"
        log.write_text("Output written on main.pdf (2 pages, 1000 bytes).")
        self.assertEqual("PASS", logs.summarize(log, 0)["status"])
        self.assertEqual("INCOMPLETE", logs.summarize(log)["status"])
        self.assertEqual("FAIL", logs.summarize(log, 1)["status"])

    def test_rerun_required_build_is_incomplete(self):
        log = self.base / "build.log"
        log.write_text("Output written on main.pdf (2 pages, 1000 bytes).\nPlease (re)run Biber on the file.")
        self.assertEqual("INCOMPLETE", logs.summarize(log, 0)["status"])

    def test_fatal_build_rejected(self):
        log = self.base / "build.log"
        log.write_text("! Undefined control sequence.\n")
        self.assertEqual("FAIL", logs.summarize(log, 0)["status"])

    def test_ieee_profile_needs_explicit_venue(self):
        registry = json.loads((ROOT / "references/writing-source-routing.json").read_text())
        request = {"schema_version": 1, "task_id": "style", "profiles": ["ieee_math_typesetting"], "declared_layers": ["L2", "L8"]}
        self.assertEqual("INVALID", router.route(request, registry)["status"])
        request["venue_profile"] = "IEEE target"
        self.assertEqual("READY", router.route(request, registry)["status"])

    def test_generic_integrity_does_not_impose_ieee(self):
        registry = json.loads((ROOT / "references/writing-source-routing.json").read_text())
        request = {"schema_version": 1, "task_id": "integrity", "profiles": ["integrity_compliance"], "declared_layers": ["L9"]}
        self.assertEqual(["revision_rubric"], [item["source_key"] for item in router.route(request, registry)["required_sources"]])

    def test_failed_inventory_rejected(self):
        registry = json.loads((ROOT / "references/writing-source-routing.json").read_text())
        request = {"schema_version": 1, "task_id": "review", "profiles": ["review_boundary"], "declared_layers": ["L0"]}
        self.assertEqual("INVALID", router.route(request, registry, {"status": "error"})["status"])

    def test_ledger_missing_local_evidence_rejected(self):
        document = json.loads((ROOT / "references/review-ledger.example.json").read_text())
        document["comments"][0]["evidence"][0]["file"] = "missing.tex"
        self.assertFalse(ledger.validate_document(document, [], self.base)["valid"])

    def test_ledger_existing_anchor_verified(self):
        document = json.loads((ROOT / "references/review-ledger.example.json").read_text())
        document["comments"][0]["evidence"][0].update(file="candidate.tex", anchor="measured residual")
        result = ledger.validate_document(document, [], self.base)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(1, result["checked_anchor_count"])

    def test_ledger_schema_mode_explicit(self):
        document = json.loads((ROOT / "references/review-ledger.example.json").read_text())
        self.assertEqual("STRUCTURE_ONLY", ledger.validate_document(document, [])["verification_scope"])


if __name__ == "__main__":
    unittest.main()
