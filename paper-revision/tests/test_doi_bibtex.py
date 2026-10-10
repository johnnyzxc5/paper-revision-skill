"""Offline fixtures and mocked HTTP; these are not live integration checks."""

import contextlib
import importlib.util
import io
import json
from email.message import Message
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "doi_bibtex.py"
SPEC = importlib.util.spec_from_file_location("doi_bibtex", SCRIPT)
doi_bibtex = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doi_bibtex)
DOI = "10.1000/test"
BIB = '@article{Example2026, title={A {nested} title}, year=2026, doi={10.1000/test}}\n'


class FakeResponse:
    def __init__(self, body=BIB, content_type="application/x-bibtex", url=None):
        self.body = body.encode("utf-8")
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.url = url or "https://api.crossref.org/works/10.1000/test/transform/application/x-bibtex"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def getcode(self):
        return 200

    def geturl(self):
        return self.url

    def read(self, limit):
        return self.body[:limit]


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response or FakeResponse(), error, 0

    def open(self, request, timeout):
        self.calls += 1
        if self.error:
            raise self.error
        assert request.get_header("Accept") == "application/x-bibtex"
        assert request.full_url.startswith("https://doi.org/")
        assert timeout == doi_bibtex.SOCKET_TIMEOUT
        return self.response


class DoiBibtexTests(unittest.TestCase):
    def run_cli(self, args):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = doi_bibtex.main(args)
        return code, json.loads(stream.getvalue())

    def test_normalization_and_url_safety(self):
        self.assertEqual(doi_bibtex.normalize_doi(" DOI:10.1000/TEST "), DOI)
        self.assertEqual(doi_bibtex.normalize_doi("https://doi.org/10.1000%2FTEST"), DOI)
        self.assertEqual(doi_bibtex.source_url("10.1000/a?b#c"), "https://doi.org/10.1000/a%3Fb%23c")
        for bad in ("https://evil.test/10.1000/test", "https://doi.org.evil.test/10.1000/test",
                    "https://user@doi.org/10.1000/test", "https://doi.org:443/10.1000/test",
                    "https://doi.org/10.1000/test?x=1", "https://doi.org/10.1000/a%0Ab",
                    "10.1000/test\nvalue", "10.1000/test\\path", "not-a-doi"):
            with self.subTest(value=bad), self.assertRaises(doi_bibtex.LookupFailure):
                doi_bibtex.normalize_doi(bad)

    def test_single_literal_doi_required(self):
        self.assertEqual(doi_bibtex.bibtex_doi(BIB), DOI)
        self.assertEqual(doi_bibtex.bibtex_doi('@article{k, month=jul, doi={10.1000/test}}'), DOI)
        self.assertEqual(doi_bibtex.bibtex_doi('@article{k, doi="HTTPS://doi.org/10.1000/TEST"}'), DOI)
        invalid = (
            "<html>Error</html>",
            '@article{k, title={doi={10.1000/test}}}',
            '@article{k, doi=someMacro}',
            '@article{k, doi={10.1000/} # {test}}',
            '@article{k, doi={10.1000/test}, doi={10.1000/other}}',
            BIB + '@article{second, doi={10.1000/test}}',
            '@article{k, doi={10.1000/test}',
        )
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(doi_bibtex.LookupFailure):
                doi_bibtex.bibtex_doi(text)

    def test_crossref_month_macro_is_preserved(self):
        # Reduced from the actual 2026-10-02 Crossref response, not a live test.
        # The unquoted month=July caused the original conservative parser to fail.
        actual_doi = "10.1038/s41586-021-03819-2"
        record = (' @article{Jumper_2021, title={Highly accurate protein structure prediction with AlphaFold}, '
                  'volume={596}, DOI={10.1038/s41586-021-03819-2}, journal={Nature}, '
                  'year={2021}, month=July, pages={583\u2013589} }\n')
        self.assertEqual(doi_bibtex.bibtex_doi(record), actual_doi)
        doi_bibtex.check_identifier(record, actual_doi)
        self.assertIn("month=July", record)

    def test_cache_hit_same_doi_has_no_network_and_preserves_original(self):
        opener = FakeOpener()
        with tempfile.TemporaryDirectory() as directory, patch.object(doi_bibtex.urllib.request, "build_opener", return_value=opener):
            code, first = self.run_cli(["--doi", "https://doi.org/10.1000/TEST", "--cache-dir", directory])
            self.assertEqual(code, 0)
            self.assertFalse(first["cache_hit"])
            original = Path(first["bibtex_file"]).read_bytes()
            metadata = json.loads(Path(first["metadata_file"]).read_text(encoding="utf-8"))
            self.assertEqual(original, BIB.encode("utf-8"))
            self.assertEqual(metadata["original_input"], "https://doi.org/10.1000/TEST")
            self.assertEqual(metadata["source_url"], "https://doi.org/10.1000/test")
            self.assertEqual(metadata["claim_support"], "not_assessed")
            code, second = self.run_cli(["--doi", DOI, "--cache-dir", directory, "--offline"])
            self.assertEqual(code, 0)
            self.assertTrue(second["cache_hit"])
            self.assertEqual(opener.calls, 1)
            self.assertEqual(Path(second["bibtex_file"]).read_bytes(), original)

    def test_wrong_doi_html_and_network_errors_never_cache_success(self):
        cases = (
            (FakeOpener(FakeResponse(BIB.replace(DOI, "10.1000/other"))), "identifier_mismatch"),
            (FakeOpener(FakeResponse("<html>Error</html>", "text/html")), "unexpected_content"),
            (FakeOpener(error=urllib.error.URLError("fixture failure")), "network_error"),
            (FakeOpener(error=urllib.error.HTTPError("https://doi.org/" + DOI, 404, "Not found", {}, None)), "http_error"),
            (FakeOpener(FakeResponse(url="http://api.crossref.org/record")), "redirect_rejected"),
        )
        for opener, expected in cases:
            with self.subTest(error=expected), tempfile.TemporaryDirectory() as directory, patch.object(doi_bibtex.urllib.request, "build_opener", return_value=opener):
                code, summary = self.run_cli(["--doi", DOI, "--cache-dir", directory])
                self.assertEqual(code, 1)
                self.assertEqual(summary["code"], expected)
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_offline_cache_miss_and_tamper_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(doi_bibtex, "fetch_record") as fetch:
            code, summary = self.run_cli(["--doi", DOI, "--cache-dir", directory, "--offline"])
            self.assertEqual((code, summary["code"]), (1, "cache_miss"))
            fetch.assert_not_called()
        with tempfile.TemporaryDirectory() as directory, patch.object(doi_bibtex.urllib.request, "build_opener", return_value=FakeOpener()):
            code, summary = self.run_cli(["--doi", DOI, "--cache-dir", directory])
            self.assertEqual(code, 0)
            Path(summary["bibtex_file"]).write_text(BIB + "% changed", encoding="utf-8")
            with patch.object(doi_bibtex, "fetch_record") as fetch:
                code, summary = self.run_cli(["--doi", DOI, "--cache-dir", directory, "--offline"])
                self.assertEqual((code, summary["code"]), (1, "invalid_cache"))
                fetch.assert_not_called()

    def test_output_and_sidecar_cannot_be_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "existing.bib"
            output.write_text("preserve bibliography", encoding="utf-8")
            with patch.object(doi_bibtex, "fetch_record") as fetch:
                code, summary = self.run_cli(["--doi", DOI, "--output", str(output)])
                self.assertEqual((code, summary["code"]), (1, "would_overwrite"))
                fetch.assert_not_called()
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve bibliography")
            output.unlink()
            sidecar = output.with_suffix(".metadata.json")
            sidecar.write_text("preserve metadata", encoding="utf-8")
            with patch.object(doi_bibtex, "fetch_record") as fetch:
                code, summary = self.run_cli(["--doi", DOI, "--output", str(output)])
                self.assertEqual((code, summary["code"]), (1, "would_overwrite"))
                fetch.assert_not_called()
            with patch.object(doi_bibtex.urllib.request, "build_opener", return_value=FakeOpener()):
                code, summary = self.run_cli(["--doi", DOI, "--output", str(output), "--overwrite"])
                self.assertEqual(code, 0)
            self.assertEqual(output.read_bytes(), BIB.encode("utf-8"))
            self.assertEqual(json.loads(sidecar.read_text(encoding="utf-8"))["doi"], DOI)

    def test_failed_refresh_preserves_existing_cache(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(doi_bibtex.urllib.request, "build_opener", return_value=FakeOpener()):
            _, initial = self.run_cli(["--doi", DOI, "--cache-dir", directory])
            before = [Path(initial[key]).read_bytes() for key in ("bibtex_file", "metadata_file")]
            with patch.object(doi_bibtex.urllib.request, "build_opener", return_value=FakeOpener(error=urllib.error.URLError("offline"))):
                code, summary = self.run_cli(["--doi", DOI, "--cache-dir", directory, "--refresh"])
                self.assertEqual((code, summary["code"]), (1, "network_error"))
            after = [Path(initial[key]).read_bytes() for key in ("bibtex_file", "metadata_file")]
            self.assertEqual(before, after)

    def test_network_total_timeout_is_bounded(self):
        gate = doi_bibtex.threading.Event()
        def delayed(doi):
            gate.wait(1)
            return BIB, doi_bibtex.source_url(doi)
        with patch.object(doi_bibtex, "TOTAL_TIMEOUT", 0.01), patch.object(doi_bibtex, "_request_bibtex", side_effect=delayed):
            try:
                with self.assertRaises(doi_bibtex.LookupFailure) as error:
                    doi_bibtex.fetch_record(DOI, DOI)
                self.assertEqual(error.exception.code, "network_timeout")
            finally:
                gate.set()


if __name__ == "__main__":
    unittest.main()
