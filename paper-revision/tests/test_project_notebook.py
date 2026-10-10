"""Project isolation, custom role policy, hashes, and optional Git state."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import project_notebook_guard as guard


class ProjectNotebookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.doc = {"schema_version": 1, "project": "Materials study", "notebook_alias": "project",
                    "notebook_title": "My materials notebook", "notebook_id": "synthetic-notebook",
                    "snapshot": {"id": "v1", "generated_at_utc": "2026-01-01T00:00:00Z"},
                    "managed_sources": []}
        for role in ("project_context", "current_manuscript"):
            file = self.repo / f"{role}.md"
            file.write_text("Synthetic paper context", encoding="utf-8")
            self.doc["managed_sources"].append({"role": role, "title": f"Author-chosen {role}",
                "source_id": f"synthetic-{role}", "local_path": file.name,
                "sha256": hashlib.sha256(file.read_bytes()).hexdigest(), "required": True})

    def validate(self):
        return guard.validate_manifest(self.doc, self.repo, check_git=False)

    def test_no_reviewers_and_no_git_accept_custom_titles(self):
        result = self.validate()
        self.assertEqual("CURRENT", result["status"], result["errors"])

    def test_reviewer_role_is_required_only_when_configured(self):
        self.doc["required_roles"] = ["project_context", "current_manuscript", "reviewer_ledger"]
        self.assertEqual("INVALID", self.validate()["status"])

    def test_changed_manuscript_is_stale(self):
        (self.repo / "current_manuscript.md").write_text("Changed scientific claims")
        self.assertEqual("STALE", self.validate()["status"])

    def test_paths_cannot_escape_project(self):
        self.doc["managed_sources"][0]["local_path"] = "../unrelated.md"
        self.assertEqual("INVALID", self.validate()["status"])

    def test_digest_exclusions_cannot_escape_project(self):
        self.doc["digest_exclusions"] = ["../unrelated.md"]
        self.assertEqual("INVALID", self.validate()["status"])

    def test_duplicate_required_roles_are_invalid(self):
        self.doc["required_roles"] = ["project_context", "project_context"]
        self.assertEqual("INVALID", self.validate()["status"])

    def test_empty_required_roles_are_invalid(self):
        self.doc["required_roles"] = []
        self.assertEqual("INVALID", self.validate()["status"])


if __name__ == "__main__":
    unittest.main()
