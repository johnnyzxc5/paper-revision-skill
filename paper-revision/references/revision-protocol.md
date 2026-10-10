# Evidence-controlled revision protocol

Use this protocol for multi-comment audits, cross-version comparisons, ledger
updates, or substantive section rewrites. For Compose/Edit without reviewers,
use the author objective and current evidence; mark raw comments and reviewer
ledgers NOT_APPLICABLE and do not synthesize reviewer IDs. Read
[editorial-contract.md](editorial-contract.md) for all prose work.

## 1. Preflight manifest

Create a working manifest before conclusions:

| Class | Required evidence |
| --- | --- |
| Current truth | active `.tex`, `.bib`, figures, experiment/config code, compiled PDF |
| Reviewer intent | raw comments/annotations and nearby original text |
| Comparison | old manuscript and relevant Git history/diffs |
| Persistent state | comment ledger, ripple/dependency ledger, acronym registry |
| External grounding | exact NotebookLM notebook/source identifiers when consultation is required |

For each item record `FOUND`, `MISSING`, or `NOT_APPLICABLE`. If a required
input is missing, continue with bounded work but label conclusions that depend
on it `BLOCKED`; do not call the audit exhaustive.

Record the active branch and `git status` before edits. A dirty tree is not an
error: preserve unrelated changes and avoid broad rewrites.

## 2. Canonical reviewer ledger

Prefer a structured `review_ledger.json` as the canonical state and render a
Markdown view for humans. Each comment has this minimum shape:

```json
{
  "id": "C1",
  "reviewer": "Reviewer A",
  "requirement": "Faithful reviewer wording",
  "status": "PARTIAL",
  "severity": "MAJOR",
  "evidence": [
    {
      "file": "manuscript.tex",
      "anchor": "stable exact text or LaTeX label",
      "line": 653,
      "observation": "What is directly present"
    }
  ],
  "affected_sections": ["Methods", "Results"],
  "dependencies": ["R8", "C24"],
  "open_actions": ["Connect the empirical transient to the methodology without an analytic overclaim"],
  "notebooklm_query_ids": ["C1-theory-evidence"],
  "route_decision": {
    "file": "route-decisions/C1.json",
    "selection_state": "AWAITING_USER_APPROVAL",
    "selected_route_id": null
  },
  "rubric_findings": [
    {
      "criterion_id": "L5",
      "outcome": "PARTIAL",
      "observation": "The empirical transient is reported but not connected to the method."
    }
  ],
  "last_verified_commit": "full-or-short-hash"
}
```

Do not preserve a line number without its anchor. Lines drift; labels and exact
text make stale mappings detectable.

### Classify work and preserve the author's schedule

Optional `work_types` is a nonempty array drawn from `PROSE_FIX`,
`EVIDENCE_NEEDED`, and `AUTHOR_DECISION`; combine them when a comment needs more
than one kind of work. This describes work, not progress or severity. Evidence
requests cannot be closed merely by changing words, and choosing a route does
not mean it has been implemented.

Optional `deferred_until` is a named phase/trigger or null. Keep the actual status
`OPEN` or `PARTIAL` as justified, with a concrete open action; intentional deferral
alone is neither `BLOCKED` nor `NEEDS_DECISION`. A terminal status (`RESOLVED` or
`OBSOLETE_SCOPE`) cannot retain deferred work. In project notes, distinguish
accepted blocks from planned additions to the same section. Reading accepted
subsections for continuity does not authorize rewriting them.

When importing a legacy Markdown ledger, inspect source requirements and current
evidence item by item. Keep the original version-qualified ID in optional
`source_id`; use a unique canonical ID such as `C1` for the guard. Preserve raw
status wording and provenance in additional note fields. `APROBADO` describes a
decision, not automatic `RESOLVED`; no automatic label mapping is safe. Likewise,
deduplicate repeated source entries by their actual requirement and anchor, not
by deleting apparently similar comments. Never add fictional reviewer records
to a paper without reviewers.

A real but unnumbered reviewer comment may receive an unused local `C1`/`R1`
style tracking ID compatible with the route guard. Preserve its exact wording,
source locator and an `id_origin: LOCAL_ASSIGNED` note; omit `source_id` when no
source ID exists. Assigning a local key is not inventing a reviewer requirement
or claiming that the reviewer supplied that number. Reuse the recorded key.

Generate a new human-readable view from the validated JSON:

```text
python scripts/revision_guard.py review_ledger.json --repo . --markdown-output work/review-ledger-r2.md
```

The command refuses existing output paths and writes nothing for an invalid
ledger. The view carries mechanical counts, pending work, validation scope and
the source JSON hash. Regenerate after changing the JSON; do not maintain both
formats independently. Without `--repo`, the view is explicitly structure-only.
Literal anchors, counts and schema checks never certify scientific support.
Expected reviewer IDs come from the current paper's inspected comments; the
example ranges below are not a roster to reuse in another paper.

### Optional scoped literal absence checks

When a revision explicitly requires particular wording to disappear, record
optional `absence_checks` on that real reviewer item. This is a nonempty array
of objects with `file`, `literal` and optional `scope`; no other keys are accepted.
Use the actual inspected wording, never a generic blacklist or an example's claim.
Each `file` is a UTF-8 text file relative to `--repo` and must remain within that
root. Without `scope`, search that entire file only. To delimit a section, supply
both `scope.start_anchor` and `scope.end_anchor`, each a distinct exact string
occurring once in that file, in order and without overlap. Search from the start
anchor (included) up to the end anchor (excluded). Use stable labels or distinctive
headings, not drifting line numbers. Missing or ambiguous boundaries are errors;
never silently widen the search to the file or repository.

Matching is exact, case-sensitive text, not regex, with ordinary UTF-8/BOM and
text-mode newline handling. It does not normalize case, TeX commands or line
wrapping. Semantic equivalents, quotations, negations and scientific support
still need contextual inspection. No other file, old version, comment document
or response letter is searched unless explicitly named as a separate check.
Where legitimate quotations occur inside a declared range, select an appropriate
range or document why this literal check is unsuitable; do not automatically
exempt matching text. A passing check neither closes the item nor supplies
deletion evidence, downstream coverage, author approval or a scientific proof.

With `--repo`, any remaining occurrence prevents `RESOLVED` and `OBSOLETE_SCOPE`.
For nonterminal items it is a warning/pending result, preserving the author's
schedule. Bad paths, unreadable text or bad boundaries are errors in any state.
Without `--repo`, declared checks are `UNVERIFIED`: nonterminal records may produce
a structure-only view with a warning; terminal records fail validation. Validated
views show executed/passed counts and individual `PASS`, `FOUND` or `UNVERIFIED`
outcomes. These counts describe literal checks, not reviewer-item progress.

Legacy `negative_searches` remain compatible annotations and always produce a
warning that they were not executed. Do not interpret those strings as literals,
infer their scope, migrate them automatically, or report them as verified absence.
For `OBSOLETE_SCOPE`, retain deletion evidence; either the legacy documented
searches or new structured checks satisfy the structural search-record field.
The former still requires manual inspection, and structured checks cover only
the explicitly named literals and ranges, not every dependent artifact.

### Status proof rules

| Status | Required proof |
| --- | --- |
| `OPEN` | requirement is absent or contradicted; at least one open action |
| `PARTIAL` | some direct evidence exists; remaining gap is explicit |
| `RESOLVED` | direct current evidence, no open action, and downstream checks completed |
| `OBSOLETE_SCOPE` | deletion evidence plus negative search across dependent text/artifacts |
| `NEEDS_DECISION` | two valid alternatives with a material user/scientific choice |
| `BLOCKED` | named missing input, access failure, or unverifiable empirical fact |

An item's status cannot be inferred from a commit message, prior summary, or
NotebookLM answer alone.

Severity is a separate axis: `BLOCKER`, `MAJOR`, `MINOR`, or `EDITORIAL`. A
comment may be `OPEN` and `EDITORIAL`, or `PARTIAL` and `BLOCKER`. Use criterion
outcomes `PASS`, `PARTIAL`, `FAIL`, `NOT_APPLICABLE`, or `UNVERIFIABLE` for
rubric findings; do not convert them into reviewer-item status mechanically.

### Mechanical invariants

- Reviewer IDs are unique.
- Expected ID ranges have no gaps.
- Status counts sum to the number of unique IDs.
- `RESOLVED` has evidence and no open actions.
- `OBSOLETE_SCOPE` has deletion evidence and negative-search scope.
- Every dependency points to an existing ID or a named project invariant.
- A reported line is still near the stored anchor; otherwise mark the location
  stale and re-resolve it.

Validate the structured ledger, literal local text/label anchors and any declared
absence checks with `--repo` set to the root used by evidence.file paths. Binary
artifacts still require manual anchor checks and cannot supply literal absence
proof. Without --repo the guard checks structure only; a terminal record with
declared absence checks cannot pass that mode:

```powershell
& $python scripts/revision_guard.py review_ledger.json --expected "R1-R8,C1-C33" --repo "."
```

## 3. Cross-version mapping algorithm

Before listing internally discovered defects for a target block, publish a
reviewer census with these separate fields:

- direct reviewer IDs whose requirement and anchor govern this block;
- inherited ripple IDs that constrain it from earlier decisions;
- adjacent-block IDs found nearby but assigned elsewhere;
- internal `D...` findings found by repository, mathematical, style, or layout
  checks.

Write `NONE` for an empty category. Preserve raw-comment and ledger anchors in
the working manifest. If either source is missing or not fully inspected, state
the bounded search performed and do not describe the result as exhaustive.

For each reviewer item, in ID order:

1. Locate the raw comment and the criticized old passage.
2. Locate the semantic equivalent in the current manuscript using labels,
   equations, distinctive phrases, figure/table captions, and citations.
3. Classify the transformation: unchanged, edited, moved, split, merged, or
   deleted.
4. Inspect every current occurrence of the affected concept, not only the first
   match.
5. Check backwards dependencies: definitions, notation, scope, abstract, and
   contribution claims.
6. Check forwards dependencies: method instantiation, experiments, results,
   limitations, conclusions, captions, tables, and bibliography.
7. Assign the provisional status using the proof table.
8. Record uncertainty as an open action or blocker; do not hide it inside prose.

For a removed baseline such as SVM, `OBSOLETE_SCOPE` requires negative searches
for the method name, acronyms, kernel terminology, comparison metrics, legends,
captions, filenames, and citations. Deleting one subsection is not enough.

## 4. Patch design

Prefer the smallest semantic patch that closes the reviewer requirement.
Before drafting final text for a substantive or ambiguous item, apply
[route-selection-gate.md](route-selection-gate.md). Generate multiple routes
only when there is a real scientific choice. Two or three distinct routes are
enough; do not manufacture cosmetic variants. A deterministic minor/editorial
fix may record `SKIPPED` with its reason.

For each candidate state:

- exact reviewer IDs addressed;
- before/after anchors;
- new claims introduced;
- required evidence/citations;
- backwards and forwards ripple effects;
- acceptance checks;
- remaining risk.

Do not change unrelated prose while resolving one comment. Broad stylistic
rewrites make attribution and regression detection harder.

Before designing a substantive patch, select only the applicable layers from
[technical-scientific-revision-rubric.md](technical-scientific-revision-rubric.md).
Scientific validity outranks prose polish. A writing change cannot close a gap
that actually requires a proof, citation, parameter, experiment, analysis, or
user decision.

Record the route decision using [route-decision.example.json](route-decision.example.json)
and validate it before drafting or applying the patch:

```powershell
& $python paper-revision/scripts/notebooklm_receipt_guard.py `
  route-decision.json --pretty
& $python paper-revision/scripts/route_guard.py route-decision.json --pretty
```

After route evaluation, use `AWAITING_USER_APPROVAL` when defensible routes are
ready for selection, `NEEDS_HUMAN_DECISION` when the objective/scope or another
material choice remains unresolved, or `BLOCKED` when no defensible route can
currently pass. Do not present an unsupported route as ready for approval.
NotebookLM may be `NOT_REQUIRED` only when the skill and project policy permit
local evaluation from inspected evidence, with an explicit reason and no
NotebookLM attribution. A required service failure remains `BLOCKED`.
`SELECTED` requires an explicit post-presentation user response choosing one
`RECOMMENDED` or `VIABLE` route and `PASS` on hard criteria `RG1`, `RG2`, `RG3`,
and `RG7`. Route selection never replaces the later L0--L10 evaluation or the
separate user approval of the exact manuscript text.

## 5. NotebookLM decision gate

Use NotebookLM only after local facts are extracted. A reviewer-driven prompt preserves
the reviewer wording and maps it to a scientific need; a Compose/Edit prompt
uses the author objective. Candidate prompts include the exact candidate text; NotebookLM cannot see
the local repository.

Run independent theory and writing queries concurrently only when they target
different notebooks and both specialties are applicable. During route selection,
send each notebook only its assigned RG criteria. Map query IDs to real reviewer
IDs when reviewers exist; for Compose/Edit without reviewers, map them to the
task ID and stable block/claim anchors. Never invent reviewer IDs for routing.
Preserve the complete JSON output as an audit artifact, but return
only the wrapper's compact decision card to the agent context.

Every route/candidate query must use a stable logical query ID, save the exact
prompt file, and preserve the complete wrapper JSON unchanged. Record those
paths, the resolved notebook ID, selected source IDs, and output SHA-256 in the
route receipt manifest. A route decision may cite NotebookLM only after
`notebooklm_receipt_guard.py` verifies the prompt hash, source scope, individually successful
answer, required labels, and route IDs. A partial batch may supply successful
individual receipts; all required roles must still be covered. A list of query IDs without those files
is not evidence. If verification fails, report the consultation as `BLOCKED`;
local analysis remains explicitly provisional.

Before sending a route or candidate query, run the receipt guard in
`--check-prompt` mode for the intended phase and role. The prompt may request
criteria and output fields but cannot state their answers, label a route as the
recommended one, or prefill a preferred route or `NONE` conclusion. Preserve
failed prompts and outputs. Never overwrite audit evidence; a corrected attempt
uses a new query ID and new files and counts as the next permitted round.

Use `notebooklm_tool.py ask|batch --output-file <receipt.json>
--compact-output` for these auditable calls. Keep `diagnostics_mode=summary`
unless investigating a real transport failure. The compact card is sufficient
for ordinary orchestration; inspect the full receipt only for a named missing
label, source marker, or unresolved criterion. Never paste full transport
timelines or repeated source summaries into the manuscript-review conversation.

Writing queries must name the rubric source, list applicable layer IDs, and use
the profiles selected by `writing_source_router.py`. Pass only the router's
required source IDs; optional sources need an explicit reason. Use the rubric as
an evaluation schema and primary sources as normative evidence. Reject
normative findings without a primary-source citation marker. A response that
cites only the rubric may identify a possible defect but cannot establish an
IEEE requirement.

Accept no answer that lacks the required verdict. `INSUFFICIENT_EVIDENCE` is a
valid blocking result, not permission to improvise. Treat source-grounded claims
and model inferences separately. Use at most two route rounds and, after route
selection, at most two candidate-text audit rounds, including the final checks.
Use the exact-candidate templates from notebooklm-prompts.md in every candidate
round; there is no separate uncounted final or conflict pass. For unchanged text, a second round targets
the unresolved specialist only; changed text needs new receipts from every
required expert for its new hash, within the same two-round limit; surface any remaining disagreement.

The route handoff shown to the user must expose the audit rather than summarize
it as an opaque endorsement. Include the notebook role, query ID, a one-line
description of what was asked, source scope, each applicable `RG` criterion,
outcome, and evidence reference. Use only the categorical outcomes returned or
locally justified; do not replace them with “excellent,” “with distinction,”
or a fabricated numerical score.

## 6. Apply and verification

Before editing, present the exact candidate at the human approval gate using the
canonical candidate patch structure: target file/location, concise summary of
main changes, exact proposed LaTeX candidate block, validation/audit status, and
the explicit human approval question. For LaTeX revisions, the exact LaTeX source
is the authoritative artifact shown to the user; do not produce a redundant second
prose/Markdown-rendered representation or convert math into Markdown. Do not
reproduce the full duplicate before-text by default (a short diff or selected
snippets may be included if materially helpful).

Before presenting the candidate, the applicable theory/writing experts audit
it using its SHA-256 and a literal REVISED_TEXT_BEGIN/REVISED_TEXT_END block
in each saved prompt. Validate exact text, a unique verdict, source evidence,
and agreement between PASS and empty failed-criteria/required-change fields. Preserve their wrapper JSON and record
`candidate_notebooklm_consultation`; every required role must return a verified
`VERDICT: PASS`. Stop for the user's separate draft decision. Record the
approved candidate and run:

```powershell
& $python paper-revision/scripts/manuscript_approval_guard.py `
  manuscript-approval.json --candidate candidate.tex --pretty
```

For a valid SKIPPED editorial route gate, keep selected_route_id=null and
route approval NOT_REQUIRED; the separate exact-draft approval still applies.
Report the measured baseline build separately from a candidate build pending
application. A user-requested temporary preview build never changes the source.
Do not edit unless the guard returns `READY_TO_APPLY`. Then re-read the exact target
region because line numbers may have changed, apply the narrow approved patch,
and run:

1. target-specific token/anchor searches;
2. acronym and notation searches;
3. the route guard when the route gate applied;
4. the ledger guard with --repo set to the evidence root when a ledger applies;
5. LaTeX compilation in the project's established build route, saving the full
   compiler log to disk;
6. summarize that log with `scripts/latex_log_summary.py --exit-code <actual-code>` and inspect raw log
   lines only for a named fatal error, undefined reference/citation, or relevant
   new box warning;
7. render and visually inspect pages whose layout could change;
8. `git diff --check` and a scoped diff review.

Only after verification update a comment to `RESOLVED` or `OBSOLETE_SCOPE`.
Update ripple and acronym ledgers in the same change when their state changed.

## 7. Handoff format

The final handoff must state:

- files changed;
- reviewer IDs whose status changed, with old and new status;
- checks run and their outcome;
- NotebookLM query IDs actually completed;
- selected route ID or the recorded reason the route gate was skipped;
- unresolved items/blockers;
- whether anything was committed or pushed.

Avoid phrases such as "100% complete" unless every manifest item and invariant
was checked in the current run.

## 8. Context reuse without evidence loss

Build the semantic context envelope once per task and record hashes for the
target block, relevant definitions, reviewer evidence, and ripple ledger. Reuse
that envelope while the hashes remain unchanged. Refresh only an input whose
hash changed or an anchor newly implicated by a finding. This is a cache of
verified evidence, not a fixed line-count shortcut: do not omit a dependency
merely to reduce prompt size.
