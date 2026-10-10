#!/usr/bin/env python3
"""Retrieve one DOI's original BibTeX; never insert it into a manuscript."""

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

MAX_BYTES = 1024 * 1024
SOCKET_TIMEOUT = 10
TOTAL_TIMEOUT = 20
METADATA_HOSTS = {
    "doi.org", "api.crossref.org", "data.crosscite.org", "api.datacite.org",
    "citation.doi.org",
}


class LookupFailure(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def normalize_doi(value):
    """Accept a bare DOI, doi: prefix, or exact doi.org URL, never arbitrary URLs."""
    if not isinstance(value, str):
        raise LookupFailure("invalid_doi", "DOI must be text.")
    value = value.strip()
    if value.lower().startswith(("http://", "https://")):
        try:
            url = urllib.parse.urlsplit(value)
            if (url.hostname != "doi.org" or url.username or url.password
                    or url.port is not None or url.query or url.fragment):
                raise ValueError("Unsupported DOI URL")
            value = urllib.parse.unquote(url.path[1:], errors="strict")
        except (ValueError, UnicodeError):
            raise LookupFailure("invalid_doi", "Use a plain DOI or an exact doi.org URL.")
    elif value.lower().startswith("doi:"):
        value = value[4:].strip()
    # Conservative ASCII profile; excluded formats fail explicitly, never get guessed.
    if not re.fullmatch(r"10\.[0-9]{4,9}/[!-~]+", value) or "\\" in value:
        raise LookupFailure("invalid_doi", "DOI format is unsupported or contains whitespace/control characters.")
    return value.lower()


def source_url(doi):
    return "https://doi.org/" + urllib.parse.quote(doi, safe="/")


def bibtex_doi(text):
    """Parse one entry's literal DOI field without accepting macros or extra entries."""
    content = text.lstrip("\ufeff").strip()
    start = re.match(r"@[A-Za-z]+\s*([({])\s*[^\s,{}()]+\s*,", content)
    if not start:
        raise LookupFailure("invalid_bibtex", "Response is not a single BibTeX entry.")
    closing = "}" if start.group(1) == "{" else ")"
    index, fields = start.end(), {}
    while True:
        while index < len(content) and content[index].isspace():
            index += 1
        if index >= len(content):
            raise LookupFailure("invalid_bibtex", "Unterminated BibTeX entry.")
        if content[index] == closing:
            if content[index + 1:].strip():
                raise LookupFailure("invalid_bibtex", "Expected exactly one BibTeX entry.")
            break
        field = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", content[index:])
        if not field:
            raise LookupFailure("invalid_bibtex", "Cannot parse a BibTeX field.")
        name = field.group(1).lower()
        if name in fields:
            raise LookupFailure("invalid_bibtex", "Duplicate BibTeX field.")
        index += field.end()
        if index >= len(content) or content[index] not in '{"':
            # Preserve ordinary non-DOI macros (e.g. month= jul) without evaluating them.
            bare = re.match(r"(?:[0-9]+|[A-Za-z][A-Za-z0-9_]*)\s*(?=[,}\)])", content[index:])
            if not bare or name == "doi":
                raise LookupFailure("invalid_bibtex", "Only literal BibTeX values are supported.")
            value, index = bare.group().strip(), index + bare.end()
        else:
            delimiter, index = content[index], index + 1
            begin, depth = index, 1 if delimiter == "{" else 0
            while index < len(content):
                char = content[index]
                if char == "\\":
                    index += 2
                    continue
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth < 0:
                        raise LookupFailure("invalid_bibtex", "Unbalanced BibTeX braces.")
                    if delimiter == "{" and depth == 0:
                        break
                elif char == '"' and delimiter == '"' and depth == 0:
                    break
                index += 1
            if index >= len(content):
                raise LookupFailure("invalid_bibtex", "Unterminated BibTeX literal.")
            value, index = content[begin:index], index + 1
        fields[name] = value
        while index < len(content) and content[index].isspace():
            index += 1
        if index < len(content) and content[index] == ",":
            index += 1
        elif index >= len(content) or content[index] != closing:
            raise LookupFailure("invalid_bibtex", "Unsupported BibTeX expression.")
    if "doi" not in fields:
        raise LookupFailure("missing_identifier", "Response has no literal DOI field; identity is unverified.")
    return normalize_doi(fields["doi"])


def check_identifier(text, doi):
    if bibtex_doi(text) != doi:
        raise LookupFailure("identifier_mismatch", "Returned DOI does not match the requested DOI.")


def checked_metadata_url(value):
    try:
        url = urllib.parse.urlsplit(value)
        if (url.scheme != "https" or url.hostname not in METADATA_HOSTS
                or url.username or url.password or url.port is not None):
            raise ValueError("Unapproved metadata endpoint")
    except ValueError:
        raise LookupFailure("redirect_rejected", "Resolver redirected outside supported HTTPS metadata services.")
    return value


class MetadataRedirects(urllib.request.HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_metadata_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _request_bibtex(doi):
    request = urllib.request.Request(source_url(doi), headers={
        "Accept": "application/x-bibtex",
        "User-Agent": "paper-revision-doi-bibtex/1.0",
    })
    opener = urllib.request.build_opener(MetadataRedirects())
    try:
        with opener.open(request, timeout=SOCKET_TIMEOUT) as response:
            if response.getcode() != 200:
                raise LookupFailure("http_error", "Metadata service did not return HTTP 200.")
            content_type = response.headers.get_content_type()
            if content_type not in {"application/x-bibtex", "text/x-bibtex", "text/plain"}:
                raise LookupFailure("unexpected_content", "Metadata response is not a supported BibTeX content type.")
            resolved = checked_metadata_url(response.geturl())
            body = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise LookupFailure("http_error", "Metadata request returned HTTP %s." % exc.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise LookupFailure("network_error", "Metadata request failed; no successful record was cached.")
    if len(body) > MAX_BYTES:
        raise LookupFailure("response_too_large", "Metadata response exceeds the one MiB limit.")
    try:
        text = body.decode("utf-8")
    except UnicodeError:
        raise LookupFailure("invalid_encoding", "Metadata response is not UTF-8.")
    check_identifier(text, doi)
    return text, resolved


def fetch_record(doi, original_input):
    """Bound the complete redirect/body exchange, including slow streams, to 20 seconds."""
    result = queue.Queue(maxsize=1)

    def worker():
        try:
            result.put((True, _request_bibtex(doi)))
        except Exception as exc:
            result.put((False, exc))

    threading.Thread(target=worker, daemon=True).start()
    try:
        ok, payload = result.get(timeout=TOTAL_TIMEOUT)
    except queue.Empty:
        raise LookupFailure("network_timeout", "Metadata retrieval exceeded the 20-second total limit.")
    if not ok:
        if isinstance(payload, LookupFailure):
            raise payload
        raise LookupFailure("network_error", "Metadata retrieval failed.")
    text, resolved = payload
    return {
        "schema_version": 1, "doi": doi, "original_input": original_input,
        "source_url": source_url(doi), "resolved_url": resolved,
        "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "original_bibtex": text,
        "identifier_check": "returned_doi_matches_requested_doi",
        "claim_support": "not_assessed",
    }


def cache_paths(directory, doi):
    stem = hashlib.sha256(doi.encode("utf-8")).hexdigest()
    return Path(directory) / (stem + ".bib"), Path(directory) / (stem + ".metadata.json")


def output_paths(path):
    bib = Path(path)
    if bib.suffix.lower() != ".bib":
        raise LookupFailure("invalid_output", "--output must name a .bib file.")
    return bib, bib.with_suffix(".metadata.json")


def preflight(paths, overwrite=False):
    if not overwrite and any(os.path.lexists(path) for path in paths):
        raise LookupFailure("would_overwrite", "Destination already exists; choose another path or explicitly use --overwrite.")


def save_pair(paths, record, overwrite=False):
    preflight(paths, overwrite)
    contents = (record["original_bibtex"].encode("utf-8"),
                (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    created = []
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite:
        try:
            for path, data in zip(paths, contents):
                with path.open("xb") as stream:
                    created.append(path)
                    stream.write(data)
        except OSError:
            for path in created:
                path.unlink(missing_ok=True)
            raise
    else:
        staged = []
        try:
            for path, data in zip(paths, contents):
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                    staged.append(Path(stream.name))
                    stream.write(data)
            for temporary, path in zip(staged, paths):
                os.replace(temporary, path)
        finally:
            for temporary in staged:
                temporary.unlink(missing_ok=True)


def read_cache(paths, doi):
    if not any(os.path.lexists(path) for path in paths):
        return None
    try:
        if paths[0].stat().st_size > MAX_BYTES or paths[1].stat().st_size > 2 * MAX_BYTES:
            raise ValueError("Oversized cache")
        body = paths[0].read_bytes()
        record = json.loads(paths[1].read_text(encoding="utf-8"))
        text = body.decode("utf-8")
        stamp = dt.datetime.fromisoformat(record["retrieved_utc"])
        if (record["schema_version"] != 1 or record["doi"] != doi
                or record["source_url"] != source_url(doi)
                or record["sha256"] != hashlib.sha256(body).hexdigest()
                or record["original_bibtex"] != text
                or record["identifier_check"] != "returned_doi_matches_requested_doi"
                or record["claim_support"] != "not_assessed"
                or stamp.utcoffset() != dt.timedelta(0)):
            raise ValueError("Invalid cache record")
        checked_metadata_url(record["resolved_url"])
        check_identifier(text, doi)
        return record
    except (OSError, ValueError, KeyError, TypeError, AttributeError, LookupFailure):
        raise LookupFailure("invalid_cache", "Cache is missing, damaged, or inconsistent; use --refresh online to replace it.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doi", required=True)
    parser.add_argument("--cache-dir", help="Opt in to a local per-DOI cache.")
    parser.add_argument("--refresh", action="store_true", help="Fetch again and explicitly replace this DOI's cache.")
    parser.add_argument("--offline", action="store_true", help="Use only an existing validated cache record.")
    parser.add_argument("--output", help="Write one original .bib entry plus .metadata.json.")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly replace --output and its sidecar.")
    args = parser.parse_args(argv)
    try:
        if not args.cache_dir and not args.output:
            raise LookupFailure("missing_destination", "Provide --cache-dir or --output; BibTeX is never printed to stdout.")
        if args.offline and (not args.cache_dir or args.refresh):
            raise LookupFailure("invalid_options", "--offline requires --cache-dir and cannot be combined with --refresh.")
        if args.refresh and not args.cache_dir:
            raise LookupFailure("invalid_options", "--refresh requires --cache-dir.")
        if args.overwrite and not args.output:
            raise LookupFailure("invalid_options", "--overwrite applies only to --output.")
        doi = normalize_doi(args.doi)
        output = output_paths(args.output) if args.output else None
        cache = cache_paths(args.cache_dir, doi) if args.cache_dir else None
        if output:
            preflight(output, args.overwrite)
        if output and cache and any(a.resolve() == b.resolve() for a in output for b in cache):
            raise LookupFailure("invalid_output", "Choose an --output path outside this DOI's cache files.")
        record = read_cache(cache, doi) if cache and not args.refresh else None
        cached = record is not None
        if record is None:
            if args.offline:
                raise LookupFailure("cache_miss", "DOI is not cached; offline mode made no network request.")
            record = fetch_record(doi, args.doi)
            if cache:
                save_pair(cache, record, overwrite=args.refresh)
        if output:
            save_pair(output, record, overwrite=args.overwrite)
        delivered = output or cache
        print(json.dumps({"status": "ok", "doi": doi, "cache_hit": cached,
                          "bibtex_file": str(delivered[0].resolve()),
                          "metadata_file": str(delivered[1].resolve()),
                          "identifier_check": record["identifier_check"],
                          "claim_support": "not_assessed"}))
        return 0
    except LookupFailure as exc:
        print(json.dumps({"status": "error", "code": exc.code, "message": str(exc)}))
        return 1
    except OSError:
        print(json.dumps({"status": "error", "code": "file_error", "message": "Could not read or write a local artifact."}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
