"""Observable installation behavior in isolated temporary directories."""
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("skill_installer", ROOT / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name) / "skills"

    def test_complete_install_includes_license_and_tools(self):
        result = installer.install(self.base)
        destination = Path(result["destination"])
        self.assertTrue((destination / "SKILL.md").is_file())
        self.assertEqual((ROOT / "LICENSE").read_bytes(), (destination / "LICENSE").read_bytes())
        self.assertEqual(12, len(list((destination / "scripts").glob("*.py"))))
        self.assertFalse((destination / "tests").exists())
        self.assertFalse((destination / "notebooklm_config.json").exists())

    def test_existing_installation_is_preserved_without_update(self):
        installer.install(self.base)
        existing = self.base / installer.NAME / "local-note.txt"
        existing.write_text("Existing user's file")
        with self.assertRaises(ValueError):
            installer.install(self.base)
        self.assertEqual("Existing user's file", existing.read_text())

    def test_update_retains_previous_bytes_in_backup(self):
        installer.install(self.base)
        existing = self.base / installer.NAME / "local-note.txt"
        existing.write_text("Previous version")
        result = installer.install(self.base, update=True)
        with zipfile.ZipFile(result["backup"]) as archive:
            self.assertEqual(b"Previous version", archive.read("paper-revision/local-note.txt"))
        self.assertTrue((self.base / installer.NAME / "SKILL.md").is_file())
        self.assertFalse(existing.exists())

    def test_dry_run_creates_nothing(self):
        self.assertEqual("DRY_RUN", installer.install(self.base, dry_run=True)["status"])
        self.assertFalse(self.base.exists())

    def test_failed_publish_restores_previous_installation(self):
        installer.install(self.base)
        existing = self.base / installer.NAME / "local-note.txt"
        existing.write_text("Restore this")
        real_replace = installer.os.replace
        def fail_publish(source, destination):
            if Path(source).name == installer.NAME:
                raise OSError("Injected publication failure")
            return real_replace(source, destination)
        with mock.patch.object(installer.os, "replace", side_effect=fail_publish):
            with self.assertRaises(OSError):
                installer.install(self.base, update=True)
        self.assertEqual("Restore this", existing.read_text())

    def test_source_directory_cannot_be_replaced(self):
        with self.assertRaises(ValueError):
            installer.install(ROOT, update=True)


if __name__ == "__main__":
    unittest.main()
