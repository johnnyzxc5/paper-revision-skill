---
name: paper-revision
description: Draft, edit, audit, and revise scientific manuscripts and reviewer responses using inspected evidence, consistent notation, author decisions, and build verification. Use for scientific arguments, mathematical exposition, substantive revisions, and reviewer feedback; not isolated document formatting.
metadata:
  version: "1.0.0"
---

# Paper Revision

Develop the scientific argument from evidence, then write the minimum prose
needed to communicate it. Keep revision records outside the manuscript. Follow
the host's instruction hierarchy and the author's explicit scope and authorization.
Never treat a fluent draft, a passing script, or a notebook answer as scientific proof.

## Establish the task

Identify Compose, Edit, Reviewer revision, Response letter, or Audit. Establish
the current artifacts, target audience, venue if known, and available evidence.
Read [project adaptation](references/project-adaptation.md) for a new paper.
There is no bundled project profile, notebook account, required writing library,
reviewer roster, or scientific domain. Use the author's own project bindings.

Keep `MANUSCRIPT`, `RESPONSE_LETTER`, and `AUDIT_NOTES` distinct. With no
reviewers, use the author's objective; do not invent comments or require a ledger.
Inspect branch and dirty files if Git exists, preserving unrelated work. A paper
without Git can still be reviewed; report unavailable history honestly.

Read only the references triggered by the current action:

| Task | Read / use |
| --- | --- |
| Diagnose or draft a change | [Editorial contract](references/editorial-contract.md), [semantic context](references/semantic-context.md), [author approval](references/approval-workflow.md) |
| Compose or restructure an argument | [Drafting playbook](references/drafting-playbook.md), relevant section of [section guide](references/section-writing-guide.md) |
| Review comments or cross-version revisions | [Evidence controls](references/evidence-and-review-controls.md), relevant procedure in [revision protocol](references/revision-protocol.md), `scripts/revision_guard.py` |
| Choose a substantive correction | [Route gate](references/route-selection-gate.md), `scripts/route_guard.py` |
| Scientific or paragraph quality check | Applicable L0–L10 layers in [scientific rubric](references/technical-scientific-revision-rubric.md); venue/domain annexes only when applicable |
| Withdraw or limit a claim | [Claim history](references/claim-history.md) |
| Find or verify citations | [Bibliography workflow](references/bibliography-workflow.md); optional `scripts/doi_bibtex.py` |
| Resume work or avoid duplicate reads | [Efficient workflow](references/efficient-workflow.md); optional `scripts/context_snapshot.py` |
| Compile or verify an applied revision | [Verification](references/verification-workflow.md); `scripts/latex_log_summary.py` |
| Set up this skill's tools | [Host runtime](references/host-runtime.md) |
| Actually consult NotebookLM | [NotebookLM workflow](references/notebooklm-workflow.md), relevant [prompt](references/notebooklm-prompts.md), [query contracts](references/query-contracts.md) |
| Manage rubric or exact-block review sources | [Source management](references/source-management.md), [writing block review](references/writing-block-review.md), `scripts/notebooklm_sources.py`, `scripts/writing_review_guard.py` |
| Select writing-notebook sources | Author's source registry, [example registry](references/writing-source-routing.json), `scripts/writing_source_router.py --registry <project-registry.json>` |
| Maintain a project-context notebook | [Project notebook protocol](references/project-notebook-protocol.md), `scripts/project_notebook_guard.py` |

Scripts run with Python 3.10+; local guards require only the standard library.
Resolve paths from this skill's installed directory. Examples in `references/`
and `tests/` are templates or synthetic fixtures, never usable audit evidence.

## Scientific invariants

- Establish what the manuscript says from its current source, bibliography,
  figures, data, and executable code. Establish whether claims are supported
  from original sources, data, and derivations. Summaries are navigation aids.
- Never invent citations, measurements, parameters, proofs, reviewer intent,
  notebook output, code behavior, or venue requirements. Name missing evidence.
- Inspect the complete semantic block, controlling neighbors, inherited
  definitions, and dependent claims. Identify protected anchors and surface any
  necessary scope expansion before changing them.
- Preserve assumptions, quantifiers, dimensions, uncertainty, denominators,
  comparators, notation, and distinctions between proof, observation, and inference.
  A writing edit cannot strengthen the evidence.
- For real reviewer work, separate direct comments, inherited dependencies,
  adjacent comments, and internal findings. Bound incomplete audits explicitly.
  Track `OPEN`, `PARTIAL`, `RESOLVED`, `OBSOLETE_SCOPE`, `NEEDS_DECISION`, or
  `BLOCKED`; severity is a separate field. Resolution needs current evidence.

## Author decisions and application

The default author-review workflow has two gates for substantive, ambiguous,
or reviewer-driven changes: evaluate and present defensible routes for author
choice, then develop and audit the exact candidate for separate approval.
Read [approval workflow](references/approval-workflow.md) before drafting/applying.
Deterministic editorial repair can skip route choice with a recorded reason.
In this default workflow, apply only after `manuscript_approval_guard.py` reports
`READY_TO_APPLY` for the approved candidate hash. Material changes invalidate it.

The author's explicit authorization and higher-priority host instructions control
the workflow. Never manufacture approval records or describe prior general
authorization as approval of an exact draft the author has not seen. If the author
chooses a different review policy, record that policy honestly rather than claiming
the strict two-gate guard passed. Audit-only work does not edit the manuscript.
Publication, messages to others, or additional external actions need their own scope.

## Bounded consultation and verification

NotebookLM is optional. Use it only when requested or required by the author's
configured evidence policy. Local diffs, grammar, compilation, and known file
facts normally need no query. Missing required consultation is `BLOCKED`; optional
consultation can be `NOT_REQUIRED` with a local evidence-based justification.

Use the bundled wrapper `scripts/notebooklm_tool.py` and the author's explicit
`--config` path. Run `doctor` before the first query. Keep project, domain/theory,
and writing roles separate. Query independent roles on the same exact candidate
without feeding one verdict into the other. Save full prompts and receipts;
validate them with `scripts/notebooklm_receipt_guard.py`. Inspect cited originals
for consequential claims. Receipt guards verify consistency, not authenticity.

Use at most two route rounds and two candidate-audit rounds. Refresh required
receipts when candidate text changes. Exact-block writing review also needs local
meaning/continuity checks and full target-source fidelity. Never upload private
manuscripts or reviewer material without authorization for that external service.

After application, verify the actual diff, affected claims, citations, compilation,
and materially changed layout. Distinguish a compiled baseline, a requested
temporary preview, and the applied candidate. Stop when material issues are
resolved; optional wording alternatives do not justify repeated audits.
