# DOI-to-BibTeX with a reusable local record

Use this helper when a source already has a DOI. It avoids repeating manual metadata searches and keeps long BibTeX responses out of the conversation. It retrieves one record; it does not discover literature, insert citations into the paper, or invent missing metadata.

From the skill directory:

```powershell
python scripts/doi_bibtex.py --doi "10.1038/s41586-021-03819-2" --cache-dir "work/doi-cache" --output "work/candidate.bib"
```

Only DOI metadata requests leave the machine. The helper sends `Accept: application/x-bibtex` to `https://doi.org/<DOI>` and follows supported HTTPS registration-agency metadata redirects. This is the official [Crossref content negotiation workflow](https://www.crossref.org/documentation/retrieve-metadata/content-negotiation/) (consulted 2026-10-02). No API key or third-party package is required. One request sequence has a 20-second total deadline, a 10-second socket timeout, bounded redirects, and a one MiB response limit; no automatic retries occur.

`--cache-dir` explicitly enables caching. Entries use a hash of the normalized DOI as the filename. Each original `.bib` has a `.metadata.json` sidecar recording the input, resolver/source URL, resolved metadata URL, retrieval time in UTC, SHA-256, and original BibTeX. Cache reads recheck the hash and returned DOI. Cache hits do not contact a service.

```powershell
python scripts/doi_bibtex.py --doi "https://doi.org/10.1038/s41586-021-03819-2" --cache-dir "work/doi-cache" --offline
```

Offline mode fails on missing or inconsistent cache entries. `--refresh` explicitly retrieves again and replaces that DOI's cache; it cannot be combined with `--offline`. Without caching, provide `--output`.

Output and sidecars never overwrite existing files unless `--overwrite` is supplied. That flag replaces a single-entry output; it is not a bibliography merge. Prefer a candidate file, inspect its metadata, and deliberately merge the needed entry into the manuscript's bibliography. Preserve the original cache and record any editorial corrections separately.

Stdout contains only a compact JSON status and artifact paths. HTML responses, unmatched/missing DOI fields, network failures, and unsupported BibTeX expressions fail without creating a successful record. Supported DOI inputs are bare ASCII DOI strings, `doi:` prefixes, or exact doi.org URLs; uncommon formats or metadata hosts fail explicitly.

A matching DOI proves only that the returned identifier matches the request. Read the source and check the exact proposition, location, publication status, and corrections before marking claim support. The helper always records `claim_support: not_assessed`.

Offline verification: `python -m unittest discover -s tests -p "test_doi_bibtex.py"`. These fixtures and mocked HTTP tests do not establish live service availability.
