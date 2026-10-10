# Assigned review-source lifecycle

Use `scripts/notebooklm_sources.py` for the rubric/temporary-source workflow of
paper-revision. It calls the installed public `notebooklm-py` CLI;
`notebooklm_tool.py` continues to handle questions, budget, recovery and retries.
No library upgrade or backend change is needed for the inspected 0.8.2 CLI.

Global helper options: `--config`, `--python`, `--profile`, `--storage`, `--backend`,
`--notebook` and `--state`. Resolve these through the active project. Different
projects use different state files and task keys. The state lock serializes one
state; it is not a cross-project/server lock. Scope every writing question to its
explicit active source IDs, including during source replacement.

- `sync --key KEY --role RUBRIC --file rubric.md`: verify matching content or
  upload the new persistent version, wait, read full content, make it current,
  then remove the previous **managed** version.
- `sync --key KEY --role TEMPORARY --file target.md --candidate target.tex`:
  same process for a review block. Markdown must declare the exact candidate
  SHA-256 and contain its complete literal `REVIEW_TEXT_BEGIN/END` block.
- `verify --key KEY`: read the recorded local content/candidate and recheck the
  remote source. A mismatch records STALE; it is not a new review.
- `cleanup --key KEY --approval-file approval.json`: remove only that temporary
  source after recorded author approval of its exact unchanged candidate.
  Accepts the existing `user_draft_decision` record or `author_approval`, each
  with status APPROVED, candidate_sha256 and the real approval evidence.

Bootstrap can pass `--adopt-rubric-id UUID` with a rubric sync. This explicitly
assigns the prior operational rubric to the workflow after its canonical title
and full content are saved; books/other sources cannot be adopted by this option.
Without explicit adoption, an old unowned rubric is retained and excluded from
the new source-scoped review. Do not delete sources just because names match.

Local Markdown is sent as UTF-8 copied text via stdin inside one **unlabelled
literal fence**, longer than every backtick run in that file. This prevents the
observed Web Markdown conversion from removing markup or changing LaTeX/tables.
A fence language label is deliberately omitted: the observed fulltext response
appends that label to the content. The local `.md` remains the reviewed artifact;
the fence is only its transport envelope, not a new or shortened candidate.
The state journals the upload format/hash before adding a source.
Processing status is checked, then `source fulltext --json` retrieves **all**
indexed text; the normal human-readable fulltext display is truncated and cannot
be used for this check. Only line endings and outer whitespace may differ.
Do not strip Markdown, collapse internal spaces, remove mathematical symbols or
accept a fuzzy/semantic match. If the backend changes this behavior, the same
strict comparison blocks review while retaining the previous source and receipts.

All operation receipts and failures are preserved under `source-receipts`.
The state records hashes, IDs, current sources, pending writes and retired
versions. A failed mutation is not retried blindly. If add returns no ID, inspect
its receipt and live inventory using the recorded unique title before any retry.
If a later step fails, `pending` contains the returned ID. Verify/recover that
specific source with the public CLI and record the resulting receipts; do not
start another upload merely to escape a pending failure. If new content is not
verified, the old source remains current. If old retirement fails, the new source
is current and the old source is explicitly pending retirement; queries must
use only the current IDs. Inspect an abandoned state lock before removing it.

Never use source append for candidate iteration: the content and its hash would
change under the same source ID. Never use `fresh=true` for source cleanup.
Keep rubric and local receipts after completion. The source helper validates
ownership/content/recorded approval, not human identity, scientific correctness
or whether NotebookLM read the entire source. The academic review guard handles
query coverage and preserves existing author-approval gates.
