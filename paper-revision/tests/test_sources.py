"""Offline source lifecycle tests with the installed CLI's JSON envelope shapes."""
import asyncio
import copy
import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import notebooklm_sources as sources


class FakeCLI:
    def __init__(self, base):
        self.base, self.remote, self.calls = base, {}, []
        self.fail, self.lossy = None, False

    async def call(self, label, argv, text=None):
        self.calls.append(label)
        if label == self.fail:
            raise sources.transport.InputError("Injected failure")
        operation = argv[0]
        if operation == "add":
            source_id = str(uuid.uuid4())
            title = argv[argv.index("--title") + 1]
            # The observed Web backend retains the body of an unlabelled
            # fenced block. Labelled fences append the language to fulltext.
            import re
            fenced = re.fullmatch(r"(`{3,})([^\n]*)\n(.*)\n\1", text, re.S)
            content = fenced.group(3) if fenced else text
            if fenced and fenced.group(2):
                content += "\n\n" + fenced.group(2)
            self.remote[source_id] = {"id": source_id, "title": title, "content": content, "status": "ready"}
            result = {"source": {"id": source_id, "title": title}}
        elif operation == "get":
            result = {"source": self.remote[argv[1]], "found": True}
        elif operation == "fulltext":
            item = self.remote[argv[1]]
            result = {"source_id": item["id"], "title": item["title"],
                      "content": item["content"][:-5] if self.lossy else item["content"]}
        elif operation == "wait":
            result = {"status": "ready"}
        elif operation == "delete":
            self.remote.pop(argv[1])
            result = {"source_id": argv[1], "notebook_id": argv[argv.index("-n")+1], "success": True, "status": "deleted"}
        path = self.base / f"{uuid.uuid4().hex}.json"
        path.write_text(json.dumps({"operation": label, "exit_code": 0, "result": result}), encoding="utf-8")
        return result, str(path)


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.path = self.base / "state.json"
        self.state = sources.load_state(self.path, str(uuid.uuid4()))
        self.cli = FakeCLI(self.base)
        self.candidate = self.base / "candidate.tex"
        self.markdown = self.base / "target.md"
        self.update("Observed accuracy is 25%.\\n")

    def update(self, text):
        self.candidate.write_text(text, encoding="utf-8")
        self.markdown.write_text(f"CANDIDATE_SHA256: {sources.sha(self.candidate.read_bytes())}\n"
                                 f"REVIEW_TEXT_BEGIN\n{text}\nREVIEW_TEXT_END\n", encoding="utf-8")

    def sync(self, **options):
        return asyncio.run(sources.sync(self.cli, self.path, self.state, "block", self.markdown,
                                        "TEMPORARY", self.candidate, **options))

    def test_upload_and_processed_content_binding(self):
        self.assertEqual("SYNCED", self.sync()["status"])
        self.assertEqual("READY", self.state["sources"]["block"]["verification_status"])
        self.assertEqual(["add", "wait", "get", "fulltext"], self.cli.calls)

    def test_same_content_has_no_second_upload(self):
        self.sync()
        self.cli.calls.clear()
        self.assertEqual("UNCHANGED", self.sync()["status"])
        self.assertEqual(["get", "fulltext"], self.cli.calls)

    def test_replace_verifies_new_before_deleting_old(self):
        old = self.sync()["source"]["source_id"]
        self.update("Observed accuracy remains 25%.")
        self.cli.calls.clear()
        new = self.sync()["source"]["source_id"]
        self.assertNotEqual(old, new)
        self.assertNotIn(old, self.cli.remote)
        self.assertIn(new, self.cli.remote)
        self.assertLess(self.cli.calls.index("fulltext"), self.cli.calls.index("delete"))

    def test_failed_upload_retains_old_and_blocks_blind_retry(self):
        old = self.sync()["source"]["source_id"]
        self.update("A revised descriptive sentence.")
        self.cli.fail = "add"
        with self.assertRaises(sources.transport.InputError): self.sync()
        self.assertEqual(old, self.state["sources"]["block"]["source_id"])
        self.cli.fail = None
        before = len(self.cli.calls)
        with self.assertRaises(sources.transport.InputError): self.sync()
        self.assertEqual(before, len(self.cli.calls))

    def test_lossy_processed_content_cannot_become_current(self):
        self.cli.lossy = True
        with self.assertRaises(sources.transport.InputError): self.sync()
        self.assertNotIn("block", self.state["sources"])
        self.assertIn("source_id", self.state["pending"][0])

    def test_not_ready_cannot_be_verified(self):
        result = self.sync()
        self.cli.remote[result["source"]["source_id"]]["status"] = "processing"
        with self.assertRaises(sources.transport.InputError):
            asyncio.run(sources.verify_current(self.cli, self.path, self.state, "block"))
        self.assertEqual("STALE", self.state["sources"]["block"]["verification_status"])

    def test_verify_changed_local_file_does_not_upload(self):
        self.sync()
        self.update("Changed later.")
        self.cli.calls.clear()
        with self.assertRaises(sources.transport.InputError):
            asyncio.run(sources.verify_current(self.cli, self.path, self.state, "block"))
        self.assertEqual([], self.cli.calls)

    def test_wrong_candidate_in_markdown_rejected_before_network(self):
        self.markdown.write_text("A summary rather than the exact candidate.")
        with self.assertRaises(sources.transport.InputError): self.sync()
        self.assertEqual([], self.cli.calls)

    def test_cleanup_needs_author_approval_not_notebook_pass(self):
        self.sync()
        approval = self.base / "approval.json"
        approval.write_text(json.dumps({"author_approval": {"status": "PASS", "candidate_sha256": sources.sha(self.candidate.read_bytes()), "evidence": "Notebook verdict"}}))
        with self.assertRaises(sources.transport.InputError):
            asyncio.run(sources.cleanup(self.cli, self.path, self.state, "block", approval))
        self.assertNotIn("delete", self.cli.calls)

    def test_cleanup_accepts_existing_draft_decision(self):
        self.sync()
        approval = self.base / "approval.json"
        approval.write_text(json.dumps({"user_draft_decision": {"status": "APPROVED", "candidate_sha256": sources.sha(self.candidate.read_bytes()), "evidence": "Author accepted the exact shown text."}}))
        result = asyncio.run(sources.cleanup(self.cli, self.path, self.state, "block", approval))
        self.assertEqual("REMOVED", result["status"])
        self.assertNotIn("block", self.state["sources"])

    def test_cleanup_rejects_stale_approval(self):
        self.sync()
        approval = self.base / "approval.json"
        approval.write_text(json.dumps({"author_approval": {"status": "APPROVED", "candidate_sha256": "0"*64, "evidence": "Accepted earlier version."}}))
        with self.assertRaises(sources.transport.InputError):
            asyncio.run(sources.cleanup(self.cli, self.path, self.state, "block", approval))

    def test_cleanup_does_not_remove_rubric(self):
        rubric = self.base / "rubric.md"
        rubric.write_text("# A general operational rubric")
        asyncio.run(sources.sync(self.cli, self.path, self.state, "rubric", rubric, "RUBRIC"))
        with self.assertRaises(sources.transport.InputError):
            asyncio.run(sources.cleanup(self.cli, self.path, self.state, "rubric", self.base / "unused.json"))

    def test_ownership_mismatch_prevents_deletion(self):
        entry = self.sync()["source"]
        entry["managed_by"] = "someone-else"
        with self.assertRaises(sources.transport.InputError):
            asyncio.run(sources.retire(self.cli, self.state, entry))

    def test_other_notebook_state_cannot_be_reused(self):
        self.sync()
        with self.assertRaises(sources.transport.InputError):
            sources.load_state(self.path, str(uuid.uuid4()))

    def test_state_lock_refuses_parallel_mutation(self):
        with sources.state_lock(self.path):
            with self.assertRaises(sources.transport.InputError):
                with sources.state_lock(self.path): pass

    def test_verification_receipt_tampering_prevents_retirement(self):
        entry = self.sync()["source"]
        Path(entry["verification_file"]).write_text("{}")
        with self.assertRaises(sources.transport.InputError):
            asyncio.run(sources.retire(self.cli, self.state, entry))

    def test_adopt_existing_rubric_then_replace_only_that_source(self):
        old_id = str(uuid.uuid4())
        self.cli.remote[old_id] = {"id": old_id, "title": "Technical Scientific Paper Revision Rubric v1.0",
                                  "content": "# Previous operational rubric", "status": "ready"}
        rubric = self.base / "rubric.md"
        rubric.write_text("# Current operational rubric")
        result = asyncio.run(sources.sync(self.cli, self.path, self.state, "rubric", rubric, "RUBRIC", adopt_rubric_id=old_id))
        self.assertEqual("SYNCED", result["status"])
        self.assertNotIn(old_id, self.cli.remote)

    def test_adoption_cannot_claim_a_writing_manual(self):
        manual_id = str(uuid.uuid4())
        self.cli.remote[manual_id] = {"id": manual_id, "title": "Science Research Writing", "content": "A manual", "status": "ready"}
        rubric = self.base / "rubric.md"
        rubric.write_text("# Current operational rubric")
        with self.assertRaises(sources.transport.InputError):
            asyncio.run(sources.sync(self.cli, self.path, self.state, "rubric", rubric, "RUBRIC", adopt_rubric_id=manual_id))
        self.assertIn(manual_id, self.cli.remote)

    def test_cleanup_records_approval_for_historical_validation(self):
        self.sync()
        approval = self.base / "approval.json"
        approval.write_text(json.dumps({"author_approval": {"status": "APPROVED", "candidate_sha256": sources.sha(self.candidate.read_bytes()), "evidence": "Author accepted unchanged reviewed text."}}))
        asyncio.run(sources.cleanup(self.cli, self.path, self.state, "block", approval))
        self.assertEqual(sources.sha(approval.read_bytes()), self.state["retired"][0]["completion_approval_sha256"])

    def test_source_cli_preserves_unicode_stdin_and_uses_utf8_child(self):
        cli = sources.CLI(["python", "-m", "notebooklm"], self.base / "receipts")
        result = SimpleNamespace(returncode=0, stdout='{"source": {"id": "example"}}', stderr="", elapsed_ms=1)
        with mock.patch.object(sources.transport, "run_process", new=mock.AsyncMock(return_value=result)) as process:
            asyncio.run(cli.call("add", ["add", "-", "--type", "text"], "Exact UTF-8 text: α, ñ, ≤"))
            self.assertEqual(["python", "-X", "utf8"], process.call_args.args[0][:3])
            self.assertEqual("Exact UTF-8 text: α, ñ, ≤", process.call_args.kwargs["stdin_text"])

    def test_literal_transport_preserves_nested_fences_tables_and_latex(self):
        text = ('# Plot observations\n\n**Conditions:** α ≤ 2, 25.00%.\n\n'
                '| Method | MDR denominator |\n| --- | --- |\n| A | all faults |\n\n'
                '\\begin{equation}\ny_i = \\frac{x_i^2}{n_\\mathrm{fault}}.\n\\end{equation}\n\n'
                '``````````python\nprint("review data")\n``````````\n')
        self.update(text)
        entry = self.sync()["source"]
        remote = self.cli.remote[entry["source_id"]]["content"]
        self.assertEqual(sources.normalize(self.markdown.read_text(encoding="utf-8")), sources.normalize(remote))
        self.assertEqual("literal-fence/v1", entry["upload_format"])
        self.assertEqual(sources.sha(sources.literal_upload(self.markdown.read_bytes().decode("utf-8-sig")).encode()), entry["upload_sha256"])

    def test_literal_fence_has_no_language_and_cannot_close_inside_payload(self):
        text = "Start\n" + "`" * 30 + "\n\\alpha_i < 25%.\nEnd"
        upload = sources.literal_upload(text)
        first, body = upload.split("\n", 1)
        self.assertEqual("`" * 31, first)
        self.assertEqual(text + "\n" + first, body)

    def test_lossy_upload_keeps_the_attempted_transport_hash(self):
        self.cli.lossy = True
        with self.assertRaises(sources.transport.InputError): self.sync()
        entry = self.state["pending"][0]
        self.assertEqual("literal-fence/v1", entry["upload_format"])
        self.assertEqual(sources.sha(sources.literal_upload(self.markdown.read_bytes().decode("utf-8-sig")).encode()), entry["upload_sha256"])

    def test_unprotected_formatting_loss_remains_rejected(self):
        fixture = sources.read_json(ROOT / "tests/fixtures/synthetic-format-loss.json")
        remote = fixture["receipt"]["result"]
        self.assertNotEqual(sources.normalize(fixture["local_text"]), sources.normalize(remote["content"]))
        self.cli.remote[remote["source_id"]] = {"id": remote["source_id"], "title": remote["title"],
                                               "content": remote["content"], "status": "ready"}
        with self.assertRaisesRegex(sources.transport.InputError, "Processed source differs"):
            asyncio.run(sources.fetch_verified(self.cli, self.state["notebook_id"],
                        remote["source_id"], remote["title"], fixture["local_text"]))

    def test_literal_fulltext_preserves_every_character(self):
        fixture = sources.read_json(ROOT / "tests/fixtures/synthetic-literal.json")
        remote = fixture["receipt"]["result"]
        self.cli.remote[remote["source_id"]] = {"id": remote["source_id"], "title": remote["title"],
                                               "content": remote["content"], "status": "ready"}
        result, _ = asyncio.run(sources.fetch_verified(self.cli, self.state["notebook_id"],
                      remote["source_id"], remote["title"], fixture["local_text"]))
        self.assertEqual(sources.normalize(fixture["local_text"]), sources.normalize(result["content"]))

    def test_numeric_or_equation_changes_are_rejected(self):
        fixture = sources.read_json(ROOT / "tests/fixtures/synthetic-literal.json")
        remote = fixture["receipt"]["result"]
        for content in [remote["content"].replace("25.00%", "25.01%"),
                        remote["content"].replace("n_\\mathrm{fault}", "n_\\mathrm{all}"),
                        remote["content"].replace("\\caption{Synthetic values: no empirical inference.}", ""),
                        remote["content"][:-40]]:
            with self.subTest(content=content[-80:]):
                self.cli.remote[remote["source_id"]] = {"id": remote["source_id"], "title": remote["title"],
                                                       "content": content, "status": "ready"}
                with self.assertRaises(sources.transport.InputError):
                    asyncio.run(sources.fetch_verified(self.cli, self.state["notebook_id"],
                                remote["source_id"], remote["title"], fixture["local_text"]))


if __name__ == "__main__": unittest.main()
