# Evidence and reviewer controls

## Evidence precedence

For questions about current project contents and revision state, use this order:

1. current manuscript, bibliography, figures, data, and executable experiment
   code on the active branch;
2. raw reviewer comments and their anchored context;
3. repository history and the old manuscript;
4. maintained audit ledgers;
5. NotebookLM source-grounded answers;
6. prior agent summaries, plans, and walkthroughs.

Lower-ranked material may reveal what to inspect, but cannot overwrite higher-
ranked evidence. A written claim is not proof of its scientific validity.
Use original technical sources, data, and code to establish validity; use the
current venue instructions to establish editorial requirements. User writing
preferences are author-side style criteria, not invented external rules.
A previous statement that a comment is resolved is a hypothesis until verified
in the current manuscript.

## Non-negotiable controls

- Inventory every required file and record missing inputs before claiming a
  complete audit.
- Preserve the reviewer's original wording or a faithful quotation alongside
  any paraphrase.
- Track comments with stable text/label anchors. Line numbers are optional
  volatile metadata, never the only evidence.
- Use exactly one canonical status per item: `OPEN`, `PARTIAL`, `RESOLVED`,
  `OBSOLETE_SCOPE`, `NEEDS_DECISION`, or `BLOCKED`.
- Track defect severity separately as `BLOCKER`, `MAJOR`, `MINOR`, or
  `EDITORIAL`; severity never substitutes for progress status.
- Mark `RESOLVED` only after direct evidence and downstream checks pass.
- Mark `OBSOLETE_SCOPE` only after proving that the criticized element and its
  dependent claims, figures, tables, citations, and comparisons are absent.
- Recompute totals mechanically. The sum of status counts must equal the number
  of unique reviewer IDs.
- Separate evidence from judgment. Use `observed`, `inferred`, and `proposed`
  labels in audit notes.
- Begin every block diagnosis with a visible reviewer census. Report direct
  comment IDs, inherited ripple IDs, adjacent-block IDs, and internally found
  defects as four separate categories. Write `NONE` explicitly when a category
  is empty. Do not infer that a block needs no correction merely because it has
  no direct reviewer comment.
- Call a reviewer census complete only when the raw comments, their anchors,
  and the current ledger were all inspected. For a task with no reviewer comments,
  state that fact and use the task objective; a reviewer census is not an audit
  of unavailable or imaginary reviewers. Otherwise state the exact bounded
  scope; never write `100%`, `all`, or `the only defects` from a partial search.
- Never invent citations, experimental parameters, code behavior, reviewer
  intent, or NotebookLM output.
- Never treat an agent recommendation, NotebookLM verdict, prior authorization,
  or lack of user objection as approval. Approval must be an explicit user
  response given after the corresponding routes or exact draft were shown.
- Do not modify Git branches, commit, push, copy to Drive, or contact anyone
  unless the user explicitly asks for that action.
