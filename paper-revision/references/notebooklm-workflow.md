# NotebookLM consultation and evidence receipts

## NotebookLM routing

NotebookLM is mandatory only when the user requests it, when a substantive
claim needs grounding in the configured source notebooks, or when the project
profile requires multi-notebook review at a decision gate. It is unnecessary
for literal diffs, acronym searches, compilation, or obvious grammar fixes.

Use the bundled `scripts/notebooklm_tool.py` wrapper with the author's explicit
`--config` path. See [setup](notebooklm-setup.md). Roles are distinct:

| Notebook | Decides | Must not decide |
| --- | --- | --- |
| `project` / configured project-context notebook | Current scope, accepted decisions, reviewer state, and ripple targets at a verified snapshot | Whether domain theory or a venue rule is correct |
| `theory` / configured technical-domain notebook | Whether technical claims and derivations are supported by its sources | What the current manuscript actually contains |
| `writing` / configured writing notebook | Whether wording, structure, qualification, and style are defensible from its sources | Whether a domain claim is true |

Resolve these roles through [project-adaptation.md](project-adaptation.md).
Bind only the author's explicitly selected notebooks. No personal notebook
configuration or required source library ships with this package.

For a reviewer-driven or cross-section change, first validate the local project
snapshot and inspect the current manuscript, raw comments, and ledgers. Query
`project` only when an accepted decision, reviewer interpretation, or ripple
target remains ambiguous after that local check; do not ask it to repeat facts
already established by higher-precedence repository evidence. Consult `theory`
and `writing` independently on the same exact candidate when it changes both
technical meaning and scientific rhetoric. Run the expert queries concurrently.
Do not feed one notebook's first verdict to the other; that creates anchoring.
The local agent synthesizes. Use `project` after local verification only when a
material accepted change must be checked or checkpointed across the whole paper.

For a rubric-driven writing query, name **Technical Scientific Paper Revision
Rubric v1.1**, declare the applicable rubric layers, and scope the query to that
source plus the smallest set of primary manuals needed. The rubric selects the
checks; primary manuals establish normative rules. If NotebookLM returns no
primary-source citation marker for a normative claim, treat that claim as
`UNVERIFIABLE`. For exact-text review, follow
[writing-block-review.md](writing-block-review.md): upload the complete target
as a verified temporary Markdown/text source when it is too long for an inline
question; synchronize the persistent rubric by content hash. Do not upload a
whole-paper skeleton, reviewer ledgers or technical domain literature to provide
writing context. The local manuscript agent checks cross-section continuity and redundancy
locally and supplies only the relevant dependency context and limits.

Before any rubric-driven query in the updated workflow, synchronize/verify the
persistent local rubric with the source helper and use its `rubric_binding`.
Legacy title aliases remain for archived inputs; they do not establish currency.
Before the first rubric-driven query in a session, list the `writing` notebook
sources. Create a source-request JSON from
`references/writing-source-request.example.json`, selecting profiles that match
the atomic task, and run `writing_source_router.py` with the wrapper's source
inventory. Stop with `BLOCKED` if any required title is absent or ambiguous.
Pass exactly the router's required source IDs in `source_ids`; exact-source
reviews also include their verified target ID. Add an optional
source only with a task-specific reason recorded in the query. Naming a source
only inside the prompt does not count as source scoping.

If the router reports `SPLIT_REQUIRED`, divide the work by profile rather than
querying the whole writing library. Never select all writing sources merely
because several rubric layers apply. Registry descriptions are routing
metadata, not normative evidence.

The L0--L10 manuscript rubric belongs only in `writing`. Do not upload it to
`theory`: technical queries receive explicit technical checks derived from the
route gate and must rely on the theory notebook's primary sources. Do not upload
the route gate to any notebook; it is a local orchestration contract.

Choose domain-source scopes from the author's project policy and the scientific
question. Use known primary sources when they control an atomic claim; leave the
scope unrestricted only for a justified synthesis across that notebook. Require
the answer to identify the sources actually used. A targeted follow-up records
its purpose and relevant source IDs. Filenames or source activation are not
evidence; unsupported claims remain `INSUFFICIENT_EVIDENCE`.

Although L2 includes theory and physical consistency, the writing-source router
may use L2 only for mathematical exposition or IEEE typesetting. It must never
use writing manuals to validate a derivation, physical mechanism, stability
claim, or implementation; route those questions to `theory` and local primary
evidence.

Never optimize a `/10` score. Accept a draft only when its explicit checks pass.
Use two separate bounded phases when a route decision is required: at most two
route-selection rounds, followed—only after user route approval—by at most two
candidate-audit rounds, including the final candidate checks. There is no extra uncounted final audit. Reuse a passing receipt only while its
candidate hash and text remain unchanged. A same-text follow-up targets the
unresolved specialist; if text changes, every required expert must return a new
receipt for that exact candidate within the two-round limit. Scope its checks to
the changes and their dependencies; do not repeat the project notebook.
Route round 2 targets the unresolved specialist criterion. If evidence remains insufficient or the
notebooks disagree, report the unresolved decision instead of manufacturing
convergence.

Do not consult all three notebooks mechanically. Literal repository facts need
none; a self-contained technical proposition normally needs `theory`; a pure
editorial issue normally needs `writing`. A project query that claims current
state requires a `CURRENT` result from `project_notebook_guard.py` plus the
live source/checkpoint verification required by the project protocol. The guard
checks the local manifest and files only.

### NotebookLM evidence receipts

NotebookLM attribution requires machine-verifiable evidence. For every route
or candidate query:

1. save the exact UTF-8 prompt file;
2. assign a stable query ID such as `C1-theory-route-r1` (use
   `ask --query-id` or the batch manifest ID; `single` is not acceptable);
3. save the wrapper's complete JSON output without rewriting it;
4. record the resolved notebook ID, exact source ID list, prompt path, output
   path, and output SHA-256 in the phase's consultation receipts;
5. for routes, run `../scripts/notebooklm_receipt_guard.py` and then
   `../scripts/route_guard.py`; for candidate audits, record
   `candidate_notebooklm_consultation` and let
   `../scripts/manuscript_approval_guard.py` revalidate it.

For auditable `ask` and `batch` calls, use the wrapper's `--output-file` and
`--compact-output` options. The complete JSON receipt stays on disk for guards
and targeted inspection; stdout contains only a decision card with hashes,
criteria, evidence fields, and summarized diagnostics. Do not print, paste, or
re-read the complete receipt unless the compact card is insufficient for a
specific unresolved criterion. Use `diagnostics_mode=summary` normally and
`full` only for an actual transport postmortem.

Before sending any route or candidate prompt, run the receipt guard's
`--check-prompt` preflight with its role, phase, and route IDs. A route prompt
must describe alternatives neutrally: do not label one recommended/preferred,
preassign an `RG` outcome, fill a preferred-route field, or prefill `NONE` for
missing evidence and risks. The local recommendation is created only after the
independent answers validate. If preflight fails, repair the question without
specifying the answer; do not query NotebookLM.

Audit prompt and output paths are append-only. Never use `--overwrite-output`
for route or candidate evidence, never rewrite a prompt after its result exists,
and never reuse a query ID for a reformulated question. Preserve a failed or
malformed attempt, assign a new round/query ID and new files, and record why it
was superseded. The receipt guard rejects an output path with archived
predecessors.

The receipt guard binds the saved prompt to `request.question_sha256`, verifies
the query result and source scope, and requires the role-specific answer labels.
An agent-created summary, a claimed query ID, a terminal heartbeat, or prose
such as “approved with distinction” is not proof of consultation. Use only the
outcomes returned for named criteria; do not embellish them. If a required
receipt fails, set the consultation and route decision to `BLOCKED`, show the
local routes only as `LOCAL_PROVISIONAL`, and do not attribute any conclusion
to NotebookLM or ask the user to select from a falsely evaluated matrix.
Candidate prompts must also declare the SHA-256 of the exact candidate shown in
chat. Before `READY_TO_APPLY`, every theory/writing role used for route selection
must have a verified candidate receipt and one raw `VERDICT: PASS`. Candidate
inline prompts contain `CANDIDATE_SHA256` and one literal `REVISED_TEXT_BEGIN` /
`REVISED_TEXT_END` block matching the candidate file. Source-based writing prompts
declare the same hash, target/rubric IDs and coverage units; their receipt adds
`writing_review_file` for verification of complete processed text and local
semantic/continuity/redundancy checks. Theory audits keep the literal-text contract.
Evidence must contain
returned references or identifiable citation markers; `PASS` cannot coexist
with failed criteria or a required change. Route-phase receipts cannot be reused
as candidate approval. Hashes bind declared artifacts; they do not authenticate
Google output or prove source support. Inspect the original cited source for
critical technical or normative claims.
