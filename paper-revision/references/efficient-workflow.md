# Efficient context and review

Use this for resumed tasks or repeated inspection of the same material. Save
work through conditional reading and reuse of unchanged, previously inspected
inputs, without reducing scientific scope.

## Read and retain once

Build the full envelope in [semantic-context.md](semantic-context.md). Search
definitions, dependents and protected anchors once; record inspected locations
and unresolved questions in author-side task notes. Retain these notes and
selected reference headings while their inputs remain unchanged. A hash cannot
reconstruct an omitted definition or locate a newly added dependency.

Optional content snapshot, from the project root:

```text
python /path/to/skill/scripts/context_snapshot.py capture --root . --manifest work/context-r1.json --file manuscript.tex --file references.bib --file work/review-ledger.json
python /path/to/skill/scripts/context_snapshot.py check --manifest work/context-r1.json
```

Include all inputs supporting a conclusion: source files, candidate, ledgers,
figures/data, selected skill references, venue/notebook-source inventory snapshots.
Include a dependency inventory if files may be added/removed. The helper checks
declared files only: it cannot detect undeclared new files or remote updates.
`UNCHANGED` means those bytes match, not that the audit is complete or correct.

When bytes change, reopen changed inputs, repeat relevant dependency searches
and refresh affected evidence maps. Changed target text invalidates its candidate
audits/approval; changed support requires reassessing dependent conclusions.
After inspection, capture to a new manifest; never overwrite the old snapshot to
manufacture freshness. Across chats, reconstruct from current local artifacts
first; caches and previous summaries are only locators.

## Relocate a project explicitly

Existing schema-v1 snapshots remain supported. The stored root is absolute;
`check` never substitutes the current directory when the old location is missing.
After moving/copying the project, verify the recorded hashes against an explicitly
chosen root, then optionally save a relocated manifest:

```text
python /path/to/skill/scripts/context_snapshot.py check --manifest work/context-r1.json --root /new/project
python /path/to/skill/scripts/context_snapshot.py rebase --manifest work/context-r1.json --root /new/project --output work/context-r1-relocated.json
```

`check --root` is read-only. `rebase` writes a new manifest only if every declared
file has the recorded bytes/hash. It preserves file records and the original
capture time, records relocation provenance, and refuses existing output paths.
Relative input paths move with the root; absolute external paths stay at their
recorded locations and must also pass. For changed/missing external inputs,
inspect their new locations and capture a new revision instead of editing hashes.

CRLF/LF conversion is a byte change and correctly yields `STALE`, even when
wording is identical. Inspect the change and rebuild affected evidence before a
new capture. Do not normalize candidate/approval hashes or infer that relocation
renews a receipt, author approval, or remote notebook/source currency.

## Spend calls where they resolve uncertainty

- Load the target section guide and relevant rubric layers, not the whole library.
- Use local searches/guards for counts, hashes, citations and compiler logs.
- Ask experts bounded questions with the exact fragment, assumptions and criteria;
  do not repeat repository facts already inspected.
- Query independent required specialists concurrently, then synthesize locally.
- Reuse unchanged passing receipts only after freshness/scope checks; preserve
  live source-inventory checks required by NotebookLM protocols.
- Round 2 targets unresolved criteria; repeat passing checks only when text,
  evidence, source scope or requirements changed.
- Keep logs/receipts/maps on disk. Show the authoritative candidate once plus a
  short decision card; inspect full logs only for a named failure.
- Render affected pages after application or an explicitly requested preview;
  avoid repeated full renders for text-only intermediate candidates.

Keep the existing two route rounds plus two candidate rounds and human gates.
A local cache hit never replaces a mandatory audit. For a new paper, plan the
whole argument once but draft/audit only the approved scope.
