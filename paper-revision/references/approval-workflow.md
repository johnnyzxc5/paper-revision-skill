# Approval workflow

## Scope and authority

Use [SKILL.md](../SKILL.md) for task classification, phase selection and
conditional reference loading. This file defines the approval states and the
exact candidate presentation; it does not repeat that loading index.

For Compose/Edit without reviewers, evaluate the author's scientific objective
and record empty reviewer categories. Do not invent reviewer IDs or require
missing reviewer artifacts. A real reviewer ledger applies only when relevant.

Requests such as "revise this section", "continue", "work on it", or "fix the
paper" start the workflow. Under this workflow's default approval policy,
route choice and exact-draft approval are separate decisions; follow the host
instruction hierarchy and explicit user authorization.

## Mandatory human approval state machine

For every reviewer-driven, substantive, or ambiguous manuscript change, use
these states in order. End the current turn at each waiting state; do not carry
on with more tools while waiting for the user's choice.
If route evaluation cannot produce a defensible selectable route, record
`NEEDS_HUMAN_DECISION` for an unresolved objective/scope choice or `BLOCKED`
for missing required evidence/service. Explain that limitation before any route
approval request; never present an invalid route as ready for selection. See
[route-selection-gate.md](route-selection-gate.md) for local blockage semantics.

1. `DIAGNOSED`: first show the reviewer census (direct, inherited, adjacent,
   and internal), then the current problem, evidence, severity, affected
   locations, protected anchors, and unresolved facts.
2. `AWAITING_USER_APPROVAL` (route gate): show one to three genuinely distinct routes after
   required NotebookLM audits have been verified from saved receipts, or a
   justified `NOT_REQUIRED` local evaluation passes the route guard. A required
   service failure is `BLOCKED`, never `NOT_REQUIRED`.
   For each route show, in normal prose: what would change, each applicable
   `RG` criterion, evaluator, outcome, supporting local anchor or NotebookLM
   query ID, benefits, evidence burden, risks, and ripple effects. Briefly show
   what each notebook was asked. State the local recommendation and why, then
   ask the user to select, modify, or reject it. **Stop.** Do not draft final
   replacement text, edit files, compile, commit, or push.
3. `ROUTE_APPROVED`: record the user's post-presentation choice in
   `user_route_decision`; route approval authorizes candidate development only.
4. `AWAITING_USER_DRAFT`: synthesize the exact candidate, run at most two
   targeted expert-audit rounds, and present the candidate at the human approval
   gate using the compact candidate patch format:
   - **Target location:** file path and section/subsection;
   - **Main changes:** concise bulleted summary of modifications (a short diff or
     selected before/after snippets may be included when they materially help
     explain a change, but reproducing the full duplicate previous text is not
     mandatory by default);
   - **Exact proposed LaTeX:** the complete, authoritative LaTeX candidate code
     block (` ```latex ... ``` `) that will be applied if approved. For LaTeX
     revisions, the exact LaTeX source is the canonical artifact shown to the
     user. Do not produce a redundant second Markdown math or prose-rendered
     preview;
   - **Validation status:** summarize the candidate audits, and distinguish
     the measured baseline compilation/page count from the uncompiled candidate.
     Report candidate build as `PENDING_APPLY` unless the user requested a preview
     build in a separate temporary copy; do not imply it already compiled;
   - **Explicit human approval question:** state clearly that no source file has
     been modified yet, and ask the user to approve, revise, or reject the exact
     candidate.
   **Stop.** Do not edit the manuscript, commit, or push. A requested temporary
   preview build never authorizes applying the candidate to the source.
5. `READY_TO_APPLY`: record the user's separate approval of the exact displayed
   candidate. Hash the candidate and run `../scripts/manuscript_approval_guard.py`.
   Only a `READY_TO_APPLY` result permits editing the manuscript.
6. `APPLIED_VERIFIED`: apply only the approved candidate, then perform local
   checks, compilation, and any materially necessary visual inspection.
7. `AWAITING_GIT_AUTHORIZATION`: report the verified diff. Commit and push only
   when the user separately authorized those Git operations.

A user may select a route other than the recommendation if it passed the hard
gates. If the user asks to revise either the route or candidate, return to the
corresponding waiting state. Any material change to an approved candidate
invalidates its hash and requires presenting the updated candidate and obtaining
new draft approval. Deterministic minor/editorial fixes may record route selection
as `SKIPPED`, but the draft-approval gate still applies before manuscript editing.

`DIAGNOSED` is not a third approval gate: normally present the diagnosis and
evaluated routes together in one response. Pause earlier only when a missing
fact or authorization prevents generating defensible routes.
