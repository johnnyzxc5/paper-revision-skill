"""Offline artifact/coverage regressions; synthetic answers are not science evidence."""
import copy
import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import writing_review_guard as review_guard
import notebooklm_receipt_guard as receipt_guard
import writing_source_router as router


class WritingReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.candidate = self.base / "candidate.tex"
        self.candidate.write_text("Canopy measurements were evaluated at the plot level.\n\n"
            "The descriptive comparison uses the same observation population.\n\n"
            "\\begin{table}\n\\caption{Plot-level measurements.}\n\\begin{tabular}{lr}\n"
            "Method & Value\\\\\nA & 25\\\\\n\\end{tabular}\n\\end{table}\n", encoding="utf-8")
        self.folder = self.base / "r1"
        review_guard.prepare(self.candidate, self.folder, "ecology-block", "CANDIDATE_AUDIT")
        self.path = self.folder / "review.json"
        self.review = review_guard.load(self.path)
        self.review["context"] = "NONE: this fixture is a self-contained block; local neighbors were checked."
        self.notebook, self.rubric_id, self.manual, self.target_id = [str(uuid.uuid4()) for _ in range(4)]
        self.state_file = self.base / "sources.json"
        self.state = {"schema": "notebooklm-managed-sources/1", "notebook_id": self.notebook,
                      "sources": {}}
        self.source("rubric", Path(self.review["rubric"]["file"]), "RUBRIC", self.rubric_id)
        self.source("ecology-block", Path(self.review["target_source"]["file"]), "TEMPORARY", self.target_id)
        self.state["sources"]["ecology-block"]["candidate_sha256"] = self.review["candidate_sha256"]
        self.write_state()
        self.routing = self.base / "routing.json"
        self.routing.write_text(json.dumps({"status": "READY", "required_sources": [
            {"source_key": "revision_rubric", "source_id": self.rubric_id, "content_verified": True},
            {"source_key": "science_research_writing", "source_id": self.manual}]}))
        self.path.write_text(json.dumps(self.review))
        review_guard.make_prompt(self.path, self.routing, self.state_file, "ecology-writing-r1", "L5/L6 and EW3/EW7/EW8/EW9")
        self.review = review_guard.load(self.path)
        self.review["local_review"].update(semantic="PASS", continuity="PASS", redundancy="PASS",
            reviewed_units=[unit["id"] for unit in self.review["units"]],
            notes="Inspected complete target and relevant local transitions; this test asserts artifact binding only.")
        self.publish()

    def source(self, key, file, role, source_id):
        title = f"managed-{key}"
        saved = self.base / f"verified-{key}.json"
        saved.write_text(json.dumps({"operation": "fulltext", "exit_code": 0, "result": {
            "source_id": source_id, "title": title, "content": file.read_text(encoding="utf-8-sig")}}), encoding="utf-8")
        self.state["sources"][key] = {"role": role, "source_id": source_id, "title": title,
            "verification_status": "READY", "content_sha256": review_guard.digest(file.read_bytes()),
            "verification_file": str(saved), "verification_sha256": review_guard.digest(saved.read_bytes())}

    def write_state(self): self.state_file.write_text(json.dumps(self.state))

    def answer(self, query=None, verdict="PASS"):
        query = query or self.review["queries"][0]
        return (f"REVIEW_MODE: {self.review['mode']}\nCANDIDATE_SHA256: {self.review['candidate_sha256']}\n"
            f"COVERED_UNITS: {','.join(query['units'])}\nUNREVIEWED_UNITS: NONE\nVERDICT: {verdict}\n"
            + ("FAILED_CRITERIA: NONE\nEVIDENCE: Wording criterion [1].\nREQUIRED_CHANGE: NONE\n" if verdict == "PASS"
               else "FAILED_CRITERIA: EW9 lacks support.\nEVIDENCE: Claim calibration [1].\nREQUIRED_CHANGE: Remove unsupported explanation.\n"))

    def publish(self, answer=None, query=None):
        query = query or self.review["queries"][0]
        prompt = review_guard.normalize(Path(query["prompt_file"]).read_text(encoding="utf-8"))
        payload = {"schema": "notebooklm-agent-wrapper/2.5.2", "command": "ask", "status": "success", "result": {
            "query_id": query["query_id"], "notebook_id": self.notebook, "status": "success",
            "retrieval_method": "direct_cli", "request": {"question_sha256": review_guard.digest(prompt.encode()),
            "source_ids": query["source_ids"]}, "answer": answer or self.answer(query), "references": []}}
        output = Path(query["output_file"])
        output.write_text(json.dumps(payload), encoding="utf-8")
        query["output_sha256"] = review_guard.digest(output.read_bytes())
        self.path.write_text(json.dumps(self.review))

    def validate(self, preflight=False): return review_guard.validate(self.review, self.folder, preflight=preflight)

    def test_other_topic_without_reviewers_passes(self):
        result = self.validate()
        self.assertTrue(result["passed"], result)
        self.assertEqual("FULL", result["coverage"])

    def test_general_guidance_is_not_candidate_audit(self):
        self.publish("Provide normative editorial recommendations for evaluating a new experimental subsection.")
        self.assertFalse(self.validate()["valid"])

    def test_guidance_mode_cannot_claim_review(self):
        result = review_guard.validate({"schema_version": 1, "mode": "GUIDANCE", "claims_candidate_review": True}, self.base)
        self.assertFalse(result["valid"])

    def test_guidance_without_review_claim_is_only_guidance(self):
        result = review_guard.validate({"schema_version": 1, "mode": "GUIDANCE"}, self.base)
        self.assertEqual("GUIDANCE_ONLY", result["status"])
        self.assertFalse(result["passed"])

    def test_exact_preflight_passes_without_answer(self):
        self.review["queries"][0].pop("output_sha256")
        self.assertTrue(self.validate(True)["valid"])

    def test_candidate_changed_invalidates_review(self):
        self.candidate.write_text("Different text, same file name.")
        self.assertFalse(self.validate()["passed"])

    def test_partial_reply_cannot_claim_full_review(self):
        self.publish(self.answer().replace("COVERED_UNITS: B001,B002,B003", "COVERED_UNITS: B001"))
        self.assertFalse(self.validate()["valid"])

    def test_caption_table_units_are_not_ignored(self):
        self.assertEqual(3, len(self.review["units"]))
        self.assertIn("caption", self.candidate.read_text().splitlines()[self.review["units"][-1]["start"]])
        self.review["queries"][0]["units"] = ["B001", "B002"]
        self.assertFalse(self.validate(True)["valid"])

    def test_partial_scope_cannot_be_passing_candidate(self):
        self.review["scope"] = "PARTIAL"
        self.assertFalse(self.validate()["passed"])

    def test_lost_denominator_boundary_is_detected(self):
        self.review["constraints"].append("Recall and pooled missed detection have different denominators.")
        self.assertFalse(self.validate(True)["valid"])

    def test_missing_local_continuity_prevents_pass(self):
        self.review["local_review"]["continuity"] = "PENDING"
        result = self.validate()
        self.assertTrue(result["valid"], result)
        self.assertFalse(result["passed"])

    def test_local_review_wrong_candidate_is_rejected(self):
        self.review["local_review"]["candidate_sha256"] = "0"*64
        self.assertFalse(self.validate()["valid"])

    def test_rubric_file_changed_is_stale(self):
        changed = self.base / "new-rubric.md"
        changed.write_text("A changed rubric")
        self.review["rubric"]["file"] = str(changed)
        self.assertFalse(self.validate()["valid"])

    def test_stale_source_state_is_rejected(self):
        self.state["sources"]["ecology-block"]["verification_status"] = "STALE"
        self.write_state()
        self.assertFalse(self.validate()["valid"])

    def test_source_verification_bytes_tampered(self):
        Path(self.state["sources"]["ecology-block"]["verification_file"]).write_text("{}")
        self.assertFalse(self.validate()["valid"])

    def test_same_numbers_do_not_close_unresolved_mechanism(self):
        # Incident phrase is a regression input, not a recommended writing example.
        anchor = "The descriptive comparison uses the same observation population."
        self.review["local_review"]["claim_changes"] = [{"after": anchor,
            "classification": "UNSUPPORTED", "reason": "Proposed feature-space saturation is not established by constant-class outputs."}]
        self.assertFalse(self.validate()["passed"])

    def test_new_scientific_restatement_requires_evidence(self):
        self.review["local_review"]["claim_changes"] = [{"after": "Canopy measurements", "classification": "SUPPORTED_RESTATEMENT", "reason": "Same stated population", "evidence": []}]
        self.assertFalse(self.validate()["valid"])

    def test_valid_diagnosis_can_report_scientific_failure(self):
        self.review["mode"] = "DIAGNOSIS"
        prompt = Path(self.review["queries"][0]["prompt_file"])
        prompt.write_text(prompt.read_text().replace("REVIEW_MODE: CANDIDATE_AUDIT", "REVIEW_MODE: DIAGNOSIS"))
        self.review["local_review"]["semantic"] = "FAIL"
        self.review["local_review"]["claim_changes"] = [{"after": "Canopy measurements", "classification": "UNSUPPORTED", "reason": "An inspected limitation remains unresolved."}]
        self.publish(self.answer(verdict="FAIL"))
        result = self.validate()
        self.assertTrue(result["valid"], result)
        self.assertFalse(result["passed"])

    def test_overwritten_receipt_cannot_be_audit_evidence(self):
        Path(self.review["queries"][0]["output_file"] + ".superseded-old").write_text("{}")
        self.assertFalse(self.validate()["valid"])

    def test_mismatched_source_ids_rejected(self):
        self.review["queries"][0]["source_ids"].append(str(uuid.uuid4()))
        self.assertFalse(self.validate()["valid"])

    def test_duplicate_verdict_rejected(self):
        self.publish(self.answer() + "VERDICT: FAIL\n")
        self.assertFalse(self.validate()["valid"])

    def test_pass_with_unreviewed_units_rejected(self):
        self.publish(self.answer().replace("UNREVIEWED_UNITS: NONE", "UNREVIEWED_UNITS: B003"))
        self.assertFalse(self.validate()["valid"])

    def test_source_receipt_connects_to_existing_candidate_guard(self):
        query = self.review["queries"][0]
        receipt = {key: query[key] for key in ("query_id", "source_ids", "prompt_file", "output_file", "output_sha256")}
        receipt.update(role="writing", notebook_id=self.notebook, writing_review_file=str(self.path))
        errors = []
        receipt_guard.validate_receipt(receipt, 1, self.base, set(), errors, phase="candidate",
                                      candidate_sha256=self.review["candidate_sha256"], candidate_text=self.candidate.read_text())
        self.assertEqual([], errors)

    def test_source_receipt_cannot_bypass_full_review(self):
        query = self.review["queries"][0]
        receipt = {key: query[key] for key in ("query_id", "source_ids", "prompt_file", "output_file", "output_sha256")}
        receipt.update(role="writing", notebook_id=self.notebook)
        errors = []
        receipt_guard.validate_receipt(receipt, 1, self.base, set(), errors, phase="candidate",
                                      candidate_sha256=self.review["candidate_sha256"], candidate_text=self.candidate.read_text())
        self.assertTrue(errors)

    def test_prompt_generation_is_append_only(self):
        with self.assertRaises(ValueError):
            review_guard.make_prompt(self.path, self.routing, self.state_file, "ecology-writing-r1", "L5")

    def test_long_target_is_preserved_without_prompt_truncation(self):
        long = self.base / "long.tex"
        long.write_text("Observed values have the same population. " * 130)
        folder = self.base / "long"
        prepared = review_guard.prepare(long, folder, "long-block", "DIAGNOSIS")
        self.assertGreater(len(long.read_text()), 3500)
        self.assertEqual(long.read_text().strip(), review_guard.extract_source(Path(prepared["target_file"]).read_text()))
        self.assertLess(len(Path(self.review["queries"][0]["prompt_file"]).read_text()) + 72, 3500)

    def test_router_binds_current_rubric_id_instead_of_title(self):
        registry = review_guard.load(ROOT / "references/writing-source-routing.json")
        request = {"schema_version": 1, "task_id": "different-paper", "profiles": ["scientific_structure"],
            "declared_layers": ["L6"], "rubric_binding": {"state_file": str(self.state_file), "key": "rubric",
            "file": self.review["rubric"]["file"], "notebook_id": self.notebook}}
        inventory = {"sources": [{"id": self.rubric_id, "title": self.state["sources"]["rubric"]["title"]},
                                  {"id": self.manual, "title": "Science Research Writing For Native And Non-native Speakers.pdf"}]}
        result = router.route(request, registry, inventory)
        self.assertEqual("READY", result["status"], result)
        self.assertTrue(next(item for item in result["required_sources"] if item["source_key"] == "revision_rubric")["content_verified"])

    def test_deleted_approved_source_retains_completed_receipt_validation(self):
        approval = self.base / "approval.json"
        approval.write_text(json.dumps({"user_draft_decision": {"status": "APPROVED", "candidate_sha256": self.review["candidate_sha256"], "evidence": "Author accepted this exact version."}}))
        entry = self.state["sources"].pop("ecology-block")
        entry.update(key="ecology-block", completion_approval_file=str(approval),
                     completion_approval_sha256=review_guard.digest(approval.read_bytes()))
        self.state["retired"] = [entry]
        self.write_state()
        self.assertTrue(self.validate()["passed"])
        self.assertFalse(self.validate(True)["valid"])

    def test_retired_unapproved_iteration_cannot_be_reused(self):
        entry = self.state["sources"].pop("ecology-block")
        entry["key"] = "ecology-block"
        self.state["retired"] = [entry]
        self.write_state()
        self.assertFalse(self.validate()["passed"])

    def test_query_id_cannot_escape_revision_directory(self):
        with self.assertRaises(ValueError):
            review_guard.make_prompt(self.path, self.routing, self.state_file, "../outside-r1", "L5")

    def test_coordinated_fragment_queries_cover_full_block(self):
        first = self.review["queries"][0]
        prompt = Path(first["prompt_file"])
        prompt.write_text(prompt.read_text().replace("COVERAGE_UNITS: B001,B002,B003", "COVERAGE_UNITS: B001,B002"))
        first["units"] = ["B001", "B002"]
        self.publish(query=first)
        self.path.write_text(json.dumps(self.review))
        review_guard.make_prompt(self.path, self.routing, self.state_file, "ecology-table-r1", "Inspect caption and units", ["B003"])
        self.review = review_guard.load(self.path)
        self.publish(query=self.review["queries"][1])
        self.assertTrue(self.validate()["passed"], self.validate())

    def test_modern_inline_candidate_uses_full_review_gate(self):
        self.review["input_mode"] = "INLINE"
        self.review["queries"] = []
        self.path.write_text(json.dumps(self.review))
        review_guard.make_prompt(self.path, self.routing, self.state_file, "ecology-inline-r1", "L5/L6 and EW9")
        self.review = review_guard.load(self.path)
        self.publish()
        self.assertTrue(self.validate()["passed"], self.validate())
        query = self.review["queries"][0]
        descriptor = {key: query[key] for key in ("query_id", "source_ids", "prompt_file", "output_file", "output_sha256")}
        descriptor.update(role="writing", notebook_id=self.notebook, writing_review_file=str(self.path))
        errors = []
        receipt_guard.validate_receipt(descriptor, 1, self.base, set(), errors, phase="candidate",
                                      candidate_sha256=self.review["candidate_sha256"], candidate_text=self.candidate.read_text())
        self.assertEqual([], errors)

    def test_theory_receipt_keeps_literal_scientific_audit_contract(self):
        query = self.review["queries"][0]
        descriptor = {key: query[key] for key in ("query_id", "source_ids", "prompt_file", "output_file", "output_sha256")}
        descriptor.update(role="theory", notebook_id=self.notebook, writing_review_file=str(self.path))
        errors = []
        receipt_guard.validate_receipt(descriptor, 1, self.base, set(), errors, phase="candidate",
                                      candidate_sha256=self.review["candidate_sha256"], candidate_text=self.candidate.read_text())
        self.assertTrue(any("literal" in item or "REVISED_TEXT" in item for item in errors))

if __name__ == "__main__": unittest.main()
