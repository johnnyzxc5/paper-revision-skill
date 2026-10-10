"""Behavior of scoped literal checks; synthetic text is not paper evidence."""
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


def document(status='RESOLVED'):
    return {'comments': [{
        'id': 'C1', 'reviewer': 'Synthetic reviewer', 'requirement': 'Limit the claim.',
        'status': status, 'severity': 'MAJOR',
        'evidence': [{'file': 'paper.tex', 'anchor': 'Current evidence', 'observation': 'Inspected.'}],
        'affected_sections': ['Methods'], 'dependencies': [],
        'open_actions': [] if status in {'RESOLVED', 'OBSOLETE_SCOPE'} else ['Complete the scheduled revision.'],
        'absence_checks': [{'file': 'paper.tex', 'literal': 'unsupported guarantee'}],
    }]}


class AbsenceCheckTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.paper = self.repo / 'paper.tex'
        self.paper.write_text('Current evidence\nSupported motivation.', encoding='utf-8')
        self.source = self.root / 'ledger.json'
        self.output = self.root / 'view.md'

    def validate(self, doc):
        return guard.validate_document(doc, ['C1'], self.repo)

    def cli(self, doc, *args):
        self.source.write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')
        return subprocess.run([sys.executable, '-X', 'utf8', '-B', guard.__file__, str(self.source),
                               *args], capture_output=True, text=True, encoding='utf-8')

    def scoped(self, doc):
        doc['comments'][0]['absence_checks'][0]['scope'] = {
            'start_anchor': 'BEGIN METHODS', 'end_anchor': 'BEGIN RESULTS'}
        return doc

    def test_resolved_rejected_despite_positive_anchor_when_retired_text_remains(self):
        self.paper.write_text('Current evidence: unsupported guarantee.', encoding='utf-8')
        result = self.validate(document())
        self.assertFalse(result['valid'])
        self.assertEqual(result['checked_anchor_count'], 1)
        self.assertEqual(result['absence_check_results'][0]['outcome'], 'FOUND')
        self.assertEqual(result['passed_absence_count'], 0)

    def test_removed_phrase_passes_without_scanning_history_or_review_notes(self):
        for name in ('old-version.tex', 'reviewer-comments.md', 'response-letter.md'):
            (self.repo / name).write_text('unsupported guarantee', encoding='utf-8')
        result = self.validate(document())
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(result['checked_absence_count'], 1)
        self.assertEqual(result['passed_absence_count'], 1)

    def test_named_range_excludes_other_sections_in_same_file(self):
        self.paper.write_text('Current evidence\nunsupported guarantee in introduction\n'
            'BEGIN METHODS\nSupported motivation.\nBEGIN RESULTS\nunsupported guarantee in conclusion.',
            encoding='utf-8')
        result = self.validate(self.scoped(document()))
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(result['absence_check_results'][0]['scope'], 'ANCHOR_RANGE')

    def test_named_range_detects_inside_and_includes_start_but_excludes_end(self):
        self.paper.write_text('Current evidence\nBEGIN METHODS\nunsupported guarantee\nBEGIN RESULTS',
                              encoding='utf-8')
        self.assertFalse(self.validate(self.scoped(document()))['valid'])
        for literal, valid in [('BEGIN METHODS', False), ('BEGIN RESULTS', True)]:
            doc = self.scoped(document())
            doc['comments'][0]['absence_checks'][0]['literal'] = literal
            self.assertEqual(self.validate(doc)['valid'], valid)

    def test_missing_duplicated_or_reversed_delimiters_are_errors(self):
        for text in ('BEGIN METHODS', 'BEGIN RESULTS',
                     'BEGIN METHODS BEGIN METHODS BEGIN RESULTS',
                     'BEGIN METHODS BEGIN RESULTS BEGIN RESULTS',
                     'BEGIN RESULTS BEGIN METHODS'):
            with self.subTest(text=text):
                self.paper.write_text('Current evidence\n' + text, encoding='utf-8')
                result = self.validate(self.scoped(document()))
                self.assertFalse(result['valid'])
                self.assertEqual(result['checked_absence_count'], 0)

    def test_overlapping_delimiter_occurrences_are_ambiguous(self):
        self.paper.write_text('Current evidence\naaaa\nEND', encoding='utf-8')
        doc = document()
        doc['comments'][0]['absence_checks'][0]['scope'] = {'start_anchor': 'aaa', 'end_anchor': 'END'}
        self.assertFalse(self.validate(doc)['valid'])

    def test_overlapping_different_delimiters_are_errors(self):
        self.paper.write_text('Current evidence\nABCDE', encoding='utf-8')
        doc = document()
        doc['comments'][0]['absence_checks'][0]['scope'] = {'start_anchor': 'ABCD', 'end_anchor': 'CDE'}
        self.assertFalse(self.validate(doc)['valid'])

    def test_terminal_records_require_repo_when_checks_are_declared(self):
        for status in ('RESOLVED', 'OBSOLETE_SCOPE'):
            doc = document(status)
            doc['comments'][0]['deletion_evidence'] = ['Deleted old baseline.']
            result = guard.validate_document(doc, [])
            self.assertFalse(result['valid'])
            self.assertEqual(result['checked_absence_count'], 0)
            self.assertEqual(result['absence_check_results'][0]['outcome'], 'UNVERIFIED')
            self.assertTrue(any('--repo is required' in e for e in result['errors']))

    def test_open_structure_only_view_reports_unexecuted_check(self):
        result = self.cli(document('OPEN'), '--markdown-output', str(self.output))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['verification_scope'], 'STRUCTURE_ONLY')
        self.assertEqual(report['checked_absence_count'], 0)
        self.assertIn('UNVERIFIED', self.output.read_text(encoding='utf-8'))

    def test_partial_deferred_work_can_report_phrase_present_without_closing(self):
        self.paper.write_text('Current evidence\nunsupported guarantee.', encoding='utf-8')
        doc = document('PARTIAL')
        doc['comments'][0]['deferred_until'] = 'Final synthesis'
        result = self.validate(doc)
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(result['counts']['PARTIAL'], 1)
        self.assertEqual(result['counts']['RESOLVED'], 0)
        self.assertTrue(any('expected absence failed' in w for w in result['warnings']))

    def test_passing_absence_does_not_close_deferred_work(self):
        doc = document()
        doc['comments'][0]['deferred_until'] = 'Final synthesis'
        result = self.validate(doc)
        self.assertFalse(result['valid'])
        self.assertEqual(result['passed_absence_count'], 1)

    def test_legacy_search_notes_are_compatible_and_explicitly_unexecuted(self):
        self.paper.write_text('Current evidence\nunsupported guarantee', encoding='utf-8')
        for status in ('RESOLVED', 'OBSOLETE_SCOPE'):
            doc = document(status)
            del doc['comments'][0]['absence_checks']
            doc['comments'][0].update(negative_searches=['unsupported guarantee'],
                                      deletion_evidence=['Removed baseline.'])
            result = self.validate(doc)
            self.assertTrue(result['valid'], result['errors'])
            self.assertEqual(result['checked_absence_count'], 0)
            self.assertTrue(any('not executed' in w for w in result['warnings']))

    def test_obsolete_scope_accepts_new_checks_without_legacy_notes(self):
        doc = document('OBSOLETE_SCOPE')
        doc['comments'][0]['deletion_evidence'] = ['Removed old baseline.']
        result = self.validate(doc)
        self.assertTrue(result['valid'], result['errors'])
        self.paper.write_text('Current evidence\nunsupported guarantee', encoding='utf-8')
        self.assertFalse(self.validate(doc)['valid'])

    def test_malformed_checks_and_scope_typos_are_rejected(self):
        values = (None, [], {}, 'phrase', ['phrase'], [None], [{}],
                  [{'file': '', 'literal': 'x'}], [{'file': 'paper.tex', 'literal': ''}],
                  [{'file': 'paper.tex', 'literal': 'x', 'scpoe': {}}],
                  [{'file': 'paper.tex', 'literal': 'x', 'scope': None}],
                  [{'file': 'paper.tex', 'literal': 'x', 'scope': {'start_anchor': 'X'}}],
                  [{'file': 'paper.tex', 'literal': 'x', 'scope': {'start_anchor': 'X', 'end_anchor': 'X'}}],
                  [{'file': 'paper.tex', 'literal': 'x', 'scope': {'start_anchor': 'X', 'end_anchor': '', 'extra': 1}}])
        for value in values:
            with self.subTest(value=value):
                doc = document()
                doc['comments'][0]['absence_checks'] = value
                self.assertFalse(self.validate(doc)['valid'])

    def test_missing_file_or_binary_text_cannot_prove_absence(self):
        self.paper.unlink()
        self.assertFalse(self.validate(document())['valid'])
        self.paper.write_bytes(b'\xff\xfe\x00')
        result = self.validate(document())
        self.assertFalse(result['valid'])
        self.assertEqual(result['checked_absence_count'], 0)

    def test_paths_outside_repo_and_absolute_paths_are_rejected(self):
        outside = self.root / 'outside.tex'
        outside.write_text('Supported motivation.', encoding='utf-8')
        for name in ('../outside.tex', str(outside), str(self.paper)):
            doc = document()
            doc['comments'][0]['absence_checks'][0]['file'] = name
            self.assertFalse(self.validate(doc)['valid'])

    def test_matching_is_literal_and_case_sensitive(self):
        self.paper.write_text('Current evidence\nUnsupported guarantee.\nxaab', encoding='utf-8')
        doc = document()
        result = self.validate(doc)
        self.assertTrue(result['valid'], result['errors'])
        doc['comments'][0]['absence_checks'][0]['literal'] = 'x.*b'
        self.assertTrue(self.validate(doc)['valid'])

    def test_utf8_bom_and_newlines_are_read_consistently(self):
        self.paper.write_bytes(b'\xef\xbb\xbfCurrent evidence\r\nunsupported guarantee\r\n')
        result = self.validate(document())
        self.assertFalse(result['valid'])
        self.assertEqual(result['checked_absence_count'], 1)

    def test_multiple_checks_and_occurrence_counts_are_reported(self):
        self.paper.write_text('Current evidence\nunsupported guarantee unsupported guarantee', encoding='utf-8')
        doc = document('OPEN')
        doc['comments'][0]['absence_checks'].append({'file': 'paper.tex', 'literal': 'different claim'})
        result = self.validate(doc)
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(result['checked_absence_count'], 2)
        self.assertEqual(result['passed_absence_count'], 1)
        self.assertEqual(result['absence_check_results'][0]['occurrence_count'], 2)

    def test_failed_resolution_creates_no_markdown_and_does_not_modify_json(self):
        self.paper.write_text('Current evidence\nunsupported guarantee', encoding='utf-8')
        doc = document()
        result = self.cli(doc, '--repo', str(self.repo), '--markdown-output', str(self.output))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(json.loads(self.source.read_text(encoding='utf-8')), doc)

    def test_successful_export_includes_scope_counts_outcomes_and_exact_json_hash(self):
        doc = document()
        result = self.cli(doc, '--repo', str(self.repo), '--markdown-output', str(self.output))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        text = self.output.read_text(encoding='utf-8')
        data = json.loads(result.stdout)
        self.assertIn('LOCAL_TEXT_ANCHORS_AND_ABSENCE_CHECKS', text)
        self.assertIn('Executed: 1; passed: 1.', text)
        self.assertIn('PASS', text)
        self.assertIn(hashlib.sha256(self.source.read_bytes()).hexdigest(), text)
        self.assertEqual(data['schema'], 'academic-review-ledger-guard/1.4')

    def test_partial_export_preserves_pending_check_and_deferral(self):
        self.paper.write_text('Current evidence\nunsupported guarantee', encoding='utf-8')
        doc = document('PARTIAL')
        doc['comments'][0]['deferred_until'] = 'Final synthesis'
        result = self.cli(doc, '--repo', str(self.repo), '--markdown-output', str(self.output))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        text = self.output.read_text(encoding='utf-8')
        self.assertIn('FOUND', text)
        self.assertIn('Final synthesis', text)
        self.assertIn('| PARTIAL | 1 |', text)

    def test_plain_prose_punctuation_remains_readable(self):
        text = 'Reviewer A: per-image results (v2.2.1), 70%.'
        self.assertEqual(guard.markdown_text(text), text)

    def test_active_markdown_and_html_remain_literal(self):
        for text in ('# Heading', '- fake action', '+ fake action', '1. fake action',
                     '[link](https://example.com)', '**fake PASS**', '`code`'):
            self.assertNotEqual(guard.markdown_text(text), text)
        text = guard.markdown_text('<script>x</script>\n# RESOLVED | 100')
        self.assertNotIn('<script>', text)
        self.assertNotIn('\n# RESOLVED', text)
        self.assertIn('<br>', text)

    def test_checks_leave_canonical_document_unchanged(self):
        doc = document()
        original = copy.deepcopy(doc)
        result = self.validate(doc)
        guard.render_markdown(doc, result, 'a' * 64)
        self.assertEqual(doc, original)


if __name__ == '__main__':
    unittest.main()
