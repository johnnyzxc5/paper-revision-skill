# Withdrawn and limited claims

Use when an author withdraws, narrows or revisits a consequential scientific
claim. Keep this optional history in the project's manuscript registry, not in
the reusable skill. A reviewer objection is evidence of a concern; inspect the
scientific basis before treating it as an accepted restriction.

Each `retired_claims` entry records:

| Field | Meaning |
| --- | --- |
| `id`, `claim` | Stable local ID and exact proposition withdrawn or limited. |
| `scope` | Conditions, section anchors and dependent uses affected. |
| `reason`, `evidence` | Why it was restricted and inspected source/artifact locators. Distinguish raw reviewer wording from interpretation. |
| `replacement` | Accepted narrower statement, or null if no replacement is accepted. |
| `revisit_condition` | Evidence or changed assumptions that would permit reconsideration. |
| `state` | `PROPOSED`, `WITHDRAWN`, `LIMITED`, or `REOPENED`; proposals are not accepted decisions. |

Use only material entries; this is not a log of every stylistic edit. The optional
array in [manuscript-registry.example.json](manuscript-registry.example.json)
starts empty. Its content must come from the project, never from example cases.

When changing a related block, inspect the relevant entries and search for the
proposition and semantic equivalents in the candidate and its affected context.
Literal searches locate candidates; they do not establish semantic equivalence.
Check what the replacement implies: a softer verb or different mechanism still
needs evidence. Preserve causal, comparative, dimensional and scope boundaries.
Reusing a correct equation does not automatically justify its new interpretation.

If an actual reviewer item requires removal of exact wording, the ledger may
record scoped `absence_checks` described in
[revision-protocol.md](revision-protocol.md). This executes only the explicitly
declared literals and file/range boundaries; it does not validate this registry,
detect paraphrases or infer acceptance of a retired claim. Keep legitimate
historical quotations and the author's deferred work in their proper context.

Follow the author's schedule for downstream changes. Record affected deferred
sections for their planned synthesis pass; do not rewrite accepted or deferred
text outside the approved scope. A proposed correction is not a resolved reviewer
item until the applicable evidence and downstream work are complete.

New evidence may justify reopening a claim. Preserve the earlier reason, record
the new evidence and apply the ordinary scientific checks and approval workflow.
Do not turn retired wording into a universal blacklist or assume the reviewer
cannot be rebutted. No hash, registry entry or text-matching script can certify
scientific support.
