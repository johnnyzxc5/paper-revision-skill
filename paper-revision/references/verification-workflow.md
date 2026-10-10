# Revision execution and verification

## When this procedure applies

Use this file for an existing-manuscript baseline build, an explicitly requested
candidate preview in a separate copy, or application/final verification. A
baseline build verifies the existing source; it does not verify proposed text.
For route and draft states, use [approval-workflow.md](approval-workflow.md).

Before application, confirm the current branch, dirty files, approved scope and
exact candidate hash; require `manuscript_approval_guard.py` to report
`READY_TO_APPLY`. Apply only that candidate and preserve unrelated changes.
Keep the complete compiler log on disk and return the structured summary from
`../scripts/latex_log_summary.py`; inspect full logs for a named failure/warning.

## Verification boundary

A clean `pdflatex` exit alone is insufficient. Check at least:

- no undefined references/citations or new fatal warnings; `latex_log_summary.py`
  receives the actual compiler `--exit-code`, reports `PASS` only for a complete
  run with an output-page record and no rerun requirement, and otherwise reports
  `FAIL` or `INCOMPLETE`. Visual layout still needs its own check;
- no prohibited/project-specific tokens in the edited abstraction layer;
- equations and symbols are introduced before use;
- scientific-writing findings are tied to criterion IDs and observable defects
  rather than a generic quality score;
- the editorial contract passes: no reviewer-response leakage, unnecessary
  repetition, undefined new symbols, or repeated acronym expansions in the
  same scope; meaningful limitations and necessary reasoning are preserved;
- substantive route decisions pass `route_guard.py`, with exactly one selected
  route or an explicit unresolved state;
- every NotebookLM-attributed route finding passes
  `notebooklm_receipt_guard.py`; a bare query ID is never sufficient;
- reviewer ledger IDs and counts are internally consistent when applicable;
  use `revision_guard.py --repo <evidence-root>` to verify text anchors as well
  as structure. Binary-artifact anchors still require manual verification;
- affected later sections do not retain contradicted claims;
- the rendered pages containing changed tables, equations, figures, or page
  breaks are visually inspected.

Generate before/after PNGs only when visual layout materially changed or the
user requests them. A text-only candidate does not need an expensive render on
every intermediate iteration.

After final verification, update applicable ledgers from observed state, run the
project consistency check when material and synchronize the verified notebook
checkpoint when the project protocol requires it. Resume and context reuse follow
[efficient-workflow.md](efficient-workflow.md); a baseline build alone never
resolves reviewer items or creates a new accepted project checkpoint.
