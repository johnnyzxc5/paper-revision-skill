"""Observable ledger behavior; fixtures are synthetic, not paper evidence."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import revision_guard as guard


def ledger():
    return {'comments': [{
        'id': 'C1', 'reviewer': 'Synthetic reviewer', 'requirement': 'Report uncertainty.',
        'status': 'OPEN', 'severity': 'MAJOR', 'evidence': [],
        'open_actions': ['Inspect repeated runs.'], 'affected_sections': ['Results'],
        'dependencies': [],
    }]}


class RevisionTrackingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'ledger.json'
        self.output = self.root / 'view.md'

    def run_cli(self, document, *args):
        self.source.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')
        return subprocess.run([sys.executable, '-B', str(Path(guard.__file__)),
                               str(self.source), *args], capture_output=True, text=True)

    def test_legacy_ledger_still_passes_without_optional_fields(self):
        self.assertTrue(guard.validate_document(ledger(), ['C1'])['valid'])

    def test_multiple_work_types_preserve_progress_status(self):
        doc = ledger()
        doc['comments'][0].update(work_types=['PROSE_FIX', 'EVIDENCE_NEEDED'],
                                  source_id='v3:BB_REV7_14')
        result = guard.validate_document(doc, ['C1'])
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(result['counts']['OPEN'], 1)
        self.assertEqual(result['counts']['RESOLVED'], 0)

    def test_invalid_or_duplicate_work_types_rejected(self):
        for value in (None, [], 'PROSE_FIX', ['UNRECOGNIZED'], ['PROSE_FIX', 'PROSE_FIX'], [{}]):
            with self.subTest(value=value):
                doc = ledger()
                doc['comments'][0]['work_types'] = value
                self.assertFalse(guard.validate_document(doc, [])['valid'])

    def test_empty_source_id_or_deferral_is_invalid(self):
        for field, value in [('source_id', ''), ('source_id', None),
                             ('deferred_until', ''), ('deferred_until', [])]:
            doc = ledger()
            doc['comments'][0][field] = value
            self.assertFalse(guard.validate_document(doc, [])['valid'])

    def test_deliberate_deferral_is_open_not_blocked(self):
        doc = ledger()
        doc['comments'][0]['deferred_until'] = 'Final synthesis after new results subsections'
        result = guard.validate_document(doc, [])
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(result['counts']['OPEN'], 1)
        self.assertEqual(result['counts']['BLOCKED'], 0)

    def test_partial_section_can_preserve_completed_work_and_pending_addition(self):
        doc = ledger()
        doc['comments'][0].update(
            status='PARTIAL', evidence=[{'file': 'paper.tex', 'anchor': 'Accepted subsection',
                                       'observation': 'Existing subsection is complete.'}],
            deferred_until='Add the requested new subsection',
            open_actions=['Add a separate uncertainty subsection; retain accepted text.'])
        result = guard.validate_document(doc, [])
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(result['counts']['PARTIAL'], 1)

    def test_terminal_states_reject_deferred_work(self):
        for status in ('RESOLVED', 'OBSOLETE_SCOPE'):
            doc = ledger()
            doc['comments'][0].update(status=status, open_actions=[], deferred_until='Later',
                evidence=[{'file': 'paper.tex', 'anchor': 'A result', 'observation': 'Present.'}],
                deletion_evidence=['Removed'], negative_searches=['No dependent occurrence'])
            result = guard.validate_document(doc, [])
            self.assertFalse(result['valid'])
            self.assertTrue(any('cannot retain deferred work' in e for e in result['errors']))

    def test_cleared_deferral_allows_otherwise_resolved_record(self):
        doc = ledger()
        doc['comments'][0].update(status='RESOLVED', open_actions=[], deferred_until=None,
            evidence=[{'file': 'paper.tex', 'anchor': 'A result', 'observation': 'Present.'}])
        self.assertTrue(guard.validate_document(doc, [])['valid'])

    def test_approved_route_does_not_change_open_status(self):
        doc = ledger()
        doc['comments'][0]['route_decision'] = {
            'file': 'route.json', 'selection_state': 'SELECTED', 'selected_route_id': 'R-A'}
        result = guard.validate_document(doc, [])
        rendered = guard.render_markdown(doc, result, 'a' * 64)
        self.assertEqual(result['counts']['RESOLVED'], 0)
        self.assertIn('**OPEN**', rendered)
        self.assertIn('SELECTED', rendered)

    def test_cli_outputs_current_counts_hash_and_remaining_work(self):
        doc = ledger()
        doc['comments'][0].update(source_id='v3:BB_1', deferred_until='Final synthesis',
            work_types=['EVIDENCE_NEEDED'], source_notes='Original label: APROBADO')
        result = self.run_cli(doc, '--markdown-output', str(self.output))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        text = self.output.read_text(encoding='utf-8')
        self.assertIn(hashlib.sha256(self.source.read_bytes()).hexdigest(), text)
        self.assertIn('| OPEN | 1 |', text)
        self.assertIn('| RESOLVED | 0 |', text)
        self.assertIn('STRUCTURE_ONLY', text)
        self.assertIn('Inspect repeated runs', text)
        self.assertIn('Final synthesis', text)
        self.assertIn('APROBADO', text)
        self.assertEqual(data['counts']['OPEN'], 1)

    def test_invalid_ledger_creates_no_output(self):
        doc = ledger()
        doc['reported_counts'] = {'RESOLVED': 1}
        result = self.run_cli(doc, '--markdown-output', str(self.output))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.output.exists())

    def test_missing_local_anchor_creates_no_output(self):
        doc = ledger()
        doc['comments'][0].update(status='RESOLVED', open_actions=[], evidence=[
            {'file': 'paper.tex', 'anchor': 'Missing claim', 'observation': 'Claimed present.'}])
        (self.root / 'paper.tex').write_text('Different statement.', encoding='utf-8')
        result = self.run_cli(doc, '--repo', str(self.root), '--markdown-output', str(self.output))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.output.exists())

    def test_local_validation_scope_and_literal_anchor_are_retained(self):
        doc = ledger()
        doc['comments'][0].update(status='RESOLVED', open_actions=[], evidence=[
            {'file': 'paper.tex', 'anchor': 'A result', 'observation': 'Present.'}])
        (self.root / 'paper.tex').write_text('A result', encoding='utf-8')
        result = self.run_cli(doc, '--repo', str(self.root), '--markdown-output', str(self.output))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('LOCAL_TEXT_ANCHORS', self.output.read_text(encoding='utf-8'))
        self.assertEqual(json.loads(result.stdout)['checked_anchor_count'], 1)

    def test_output_never_overwrites_view_or_source_json(self):
        self.output.write_bytes(b'Previous view')
        doc = ledger()
        for target in (self.output, self.source):
            result = self.run_cli(doc, '--markdown-output', str(target))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(self.source.read_text(encoding='utf-8')), doc)
            self.assertEqual(self.output.read_bytes(), b'Previous view')

    def test_markdown_and_html_in_source_are_rendered_as_text(self):
        doc = ledger()
        doc['comments'][0]['requirement'] = '<script>alert(1)</script>\n# RESOLVED | 100\n[x](https://example.com)'
        result = self.run_cli(doc, '--markdown-output', str(self.output))
        self.assertEqual(result.returncode, 0)
        text = self.output.read_text(encoding='utf-8')
        self.assertNotIn('<script>', text)
        self.assertNotIn('\n# RESOLVED', text)
        self.assertNotIn('[x](https://example.com)', text)
        self.assertIn('| RESOLVED | 0 |', text)

    def test_render_does_not_change_canonical_document(self):
        doc = ledger()
        original = copy.deepcopy(doc)
        guard.render_markdown(doc, guard.validate_document(doc, []), 'a' * 64)
        self.assertEqual(doc, original)


if __name__ == '__main__':
    unittest.main()
