"""Offline tests of receipt publication and compact answer handling."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("notebooklm_wrapper_under_test", ROOT / "scripts/notebooklm_tool.py")
wrapper = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = wrapper
spec.loader.exec_module(wrapper)


class WrapperTests(unittest.TestCase):
    def test_missing_project_alias_fails_before_any_service_call(self):
        for alias in ("project", "theory", "writing"):
            with self.subTest(alias=alias), self.assertRaises(wrapper.InputError):
                wrapper.resolve_notebook(alias, {})

    def test_empty_alias_template_cannot_query_a_notebook(self):
        import json
        config = json.loads((ROOT / "references/notebooklm-config.example.json").read_text(encoding="utf-8"))
        for alias in ("project", "theory", "writing"):
            with self.subTest(alias=alias), self.assertRaises(wrapper.InputError):
                wrapper.resolve_notebook(alias, config)

    def test_custom_alias_resolves_only_its_configured_notebook(self):
        config = {"notebooks": {"writing": {"id": "synthetic-author-notebook"}}}
        self.assertEqual("synthetic-author-notebook", wrapper.resolve_notebook("writing", config))

    def test_receipt_create_and_refuse_existing(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            wrapper.write_receipt(str(path), {"status": "success"}, False)
            initial = path.read_bytes()
            with self.assertRaises(wrapper.InputError):
                wrapper.write_receipt(str(path), {"status": "error"}, False)
            self.assertEqual(initial, path.read_bytes())

    def test_exclusive_publish_refuses_racing_writer(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            real_link = wrapper.os.link
            def race(source, destination):
                Path(destination).write_text('{"other_writer": true}')
                return real_link(source, destination)
            with mock.patch.object(wrapper.os, "link", side_effect=race):
                with self.assertRaises(wrapper.InputError):
                    wrapper.write_receipt(str(path), {"status": "success"}, False)
            self.assertEqual('{"other_writer": true}', path.read_text())
            self.assertEqual([], list(path.parent.glob("*.superseded-*")))

    def test_deliberate_overwrite_archives_previous_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            wrapper.write_receipt(str(path), {"revision": 1}, False)
            initial = path.read_bytes()
            _, _, archive = wrapper.write_receipt(str(path), {"revision": 2}, True)
            self.assertEqual(initial, Path(archive["path"]).read_bytes())

    def test_bold_fields_are_visible_in_compact_card(self):
        self.assertEqual("PASS", wrapper.extract_labeled_answer("**VERDICT:** PASS\n**EVIDENCE:** [1]")["VERDICT"])

    def test_duplicate_verdict_is_flagged_in_card(self):
        result = wrapper.compact_query_result({"answer": "VERDICT: PASS\nVERDICT: FAIL", "status": "success"})
        self.assertTrue(result["answer_contract_issues"])

    def test_fresh_examples_are_nondestructive(self):
        import json
        example = json.loads((ROOT / "references/dual-query.example.json").read_text())
        self.assertTrue(all(query["fresh"] is False for query in example["queries"]))


if __name__ == "__main__":
    unittest.main()
