"""Offline invariants for declared-input freshness, including equal-size edits."""
import copy
import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import context_snapshot as context


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'paper.tex'
        self.source.write_bytes(b'claim one\n')
        self.snapshot = context.capture(self.root, ['paper.tex'])

    def test_unchanged_is_not_semantic_verification(self):
        result = context.check(self.snapshot)
        self.assertEqual(result['status'], 'UNCHANGED')
        self.assertFalse(result['semantic_verification'])

    def test_same_size_and_timestamp_change_is_detected(self):
        stat = self.source.stat()
        self.source.write_bytes(b'claim two\n')
        os.utime(self.source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        result = context.check(self.snapshot)
        self.assertEqual(result['status'], 'STALE')
        self.assertEqual(result['changed'], ['paper.tex'])

    def test_missing_file_is_stale(self):
        self.source.unlink()
        self.assertEqual(context.check(self.snapshot)['missing'], ['paper.tex'])

    def test_absolute_external_input_is_tracked(self):
        folder = self.root / 'project'
        folder.mkdir()
        snap = context.capture(folder, [str(self.source)])
        self.assertEqual(context.check(snap)['status'], 'UNCHANGED')

    def test_duplicate_and_empty_inputs_are_rejected(self):
        for names in ([], ['paper.tex', './paper.tex']):
            with self.assertRaises(ValueError):
                context.capture(self.root, names)

    def test_malformed_manifest_cannot_return_unchanged(self):
        for snapshot in ({}, {'schema_version': 1, 'root': str(self.root), 'files': []}):
            with self.assertRaises(ValueError):
                context.check(snapshot)
        snapshot = copy.deepcopy(self.snapshot)
        snapshot['files'][0]['sha256'] = 'broken'
        with self.assertRaises(ValueError):
            context.check(snapshot)

    def test_undeclared_files_do_not_expand_claimed_scope(self):
        (self.root / 'new.tex').write_bytes(b'new dependency')
        result = context.check(self.snapshot)
        self.assertEqual(result['checked_files'], 1)
        self.assertFalse(result['semantic_verification'])

    def test_cli_refuses_to_replace_existing_snapshot(self):
        manifest = self.root / 'snapshot.json'
        script = Path(context.__file__)
        command = [sys.executable, str(script), 'capture', '--root', str(self.root),
                   '--manifest', str(manifest), '--file', 'paper.tex']
        first = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        original = manifest.read_bytes()
        self.source.write_bytes(b'changed')
        second = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(second.returncode, 2)
        self.assertEqual(json.loads(second.stdout)['status'], 'INVALID')
        self.assertEqual(manifest.read_bytes(), original)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-B', str(Path(context.__file__)), *args],
                              capture_output=True, text=True)

    def relocated_root(self):
        destination = self.root / 'relocated'
        destination.mkdir()
        (destination / 'paper.tex').write_bytes(self.source.read_bytes())
        return destination

    def test_explicit_override_checks_new_root_without_mutating_snapshot(self):
        destination = self.relocated_root()
        original = copy.deepcopy(self.snapshot)
        self.source.write_bytes(b'changed at the old location')
        self.assertEqual(context.check(self.snapshot)['status'], 'STALE')
        result = context.check(self.snapshot, destination)
        self.assertEqual(result['status'], 'UNCHANGED')
        self.assertTrue(result['root_overridden'])
        self.assertEqual(self.snapshot, original)

    def test_cli_check_never_guesses_root_from_working_directory(self):
        destination = self.relocated_root()
        manifest = self.root / 'original.json'
        manifest.write_text(json.dumps(self.snapshot), encoding='utf-8')
        self.source.unlink()
        command = [sys.executable, '-B', str(Path(context.__file__)), 'check',
                   '--manifest', str(manifest)]
        result = subprocess.run(command, cwd=destination, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['missing'], ['paper.tex'])
        overridden = self.run_cli('check', '--manifest', str(manifest),
                                  '--root', str(destination))
        self.assertEqual(overridden.returncode, 0, overridden.stdout + overridden.stderr)
        self.assertEqual(manifest.read_text(encoding='utf-8'), json.dumps(self.snapshot))

    def test_rebase_preserves_hashes_and_original_manifest(self):
        destination = self.relocated_root()
        manifest, output = self.root / 'original.json', self.root / 'rebased.json'
        manifest.write_text(json.dumps(self.snapshot), encoding='utf-8')
        original = manifest.read_bytes()
        self.source.unlink()
        result = self.run_cli('rebase', '--manifest', str(manifest),
                              '--root', str(destination), '--output', str(output))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'REBASED')
        rebased = json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(rebased['files'], self.snapshot['files'])
        self.assertEqual(rebased['captured_utc'], self.snapshot['captured_utc'])
        self.assertEqual(rebased['root'], str(destination.resolve()))
        self.assertEqual(rebased['rebased_from']['root'], self.snapshot['root'])
        self.assertEqual(context.check(rebased)['status'], 'UNCHANGED')
        self.assertFalse(context.check(rebased)['semantic_verification'])
        self.assertEqual(manifest.read_bytes(), original)

    def test_rebase_refuses_changed_or_missing_inputs_without_writing(self):
        destination = self.relocated_root()
        manifest, output = self.root / 'original.json', self.root / 'rebased.json'
        manifest.write_text(json.dumps(self.snapshot), encoding='utf-8')
        target = destination / 'paper.tex'
        target.write_bytes(b'claim two\n')
        for failure in ('changed', 'missing'):
            if failure == 'missing':
                target.unlink()
            result = self.run_cli('rebase', '--manifest', str(manifest),
                                  '--root', str(destination), '--output', str(output))
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)[failure], ['paper.tex'])
            self.assertFalse(output.exists())

    def test_rebase_never_replaces_existing_or_original_manifest(self):
        destination = self.relocated_root()
        manifest, output = self.root / 'original.json', self.root / 'rebased.json'
        manifest.write_text(json.dumps(self.snapshot), encoding='utf-8')
        output.write_bytes(b'keep this existing file')
        for target in (manifest, output):
            original = target.read_bytes()
            result = self.run_cli('rebase', '--manifest', str(manifest),
                                  '--root', str(destination), '--output', str(target))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(target.read_bytes(), original)

    def test_rebase_keeps_absolute_external_inputs_at_their_recorded_path(self):
        external = self.root / 'external.txt'
        external.write_bytes(b'external evidence')
        snap = context.capture(self.root, ['paper.tex'])
        # Absolute records remain external even when their path is inside the old root.
        snap['files'].append({'path': str(external), **context.fingerprint(external)})
        destination = self.relocated_root()
        (destination / 'external.txt').write_bytes(external.read_bytes())
        external.unlink()
        result = context.check(snap, destination)
        self.assertEqual(result['status'], 'STALE')
        self.assertEqual(result['missing'], [str(external)])

    def test_line_ending_changes_remain_exact_byte_changes(self):
        self.source.write_bytes(b'claim one\r\n')
        self.assertEqual(context.check(self.snapshot)['changed'], ['paper.tex'])

    def test_relocation_rejects_invalid_roots_and_escaping_relative_records(self):
        for root in (self.source, self.root / 'does-not-exist'):
            with self.assertRaises((OSError, ValueError)):
                context.check(self.snapshot, root)
        snapshot = copy.deepcopy(self.snapshot)
        snapshot['files'][0]['path'] = '../paper.tex'
        with self.assertRaises(ValueError):
            context.check(snapshot)


if __name__ == '__main__':
    unittest.main()
