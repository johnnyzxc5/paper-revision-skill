# Route-selection gate for substantive paper revisions

Use this gate to choose **how** to resolve a reviewer requirement before
drafting final prose. For Compose/Edit without reviewers, evaluate the author
objective and scientific acceptance requirement instead of inventing a reviewer
comment. Record empty reviewer categories and anchor the actual task evidence. It is a decision protocol, not another manuscript-quality
rubric and not a numerical scoring system.

Do not upload this file to any NotebookLM notebook. The local agent owns route
selection and places only the criteria relevant to each specialist inside the
query. The writing notebook keeps the separate **Technical Scientific Paper
Revision Rubric v1.1**; the theory notebook does not need that rubric.

## 1. Activation

The gate is mandatory when at least one condition holds:

- severity is `BLOCKER` or `MAJOR`;
- two or more scientifically different corrections appear plausible;
- an equation, assumption, mechanism, theorem, scope boundary, experiment,
  figure, table, dataset, or cited evidence may change;
- resolving the item may require new evidence or removing a claim;
- the change has backwards or forwards ripple effects;
- the agent proposes a technical rebuttal instead of a manuscript change.

Skip the gate for a deterministic `MINOR` or `EDITORIAL` repair such as a known
typo, an unambiguous acronym definition, or a verified venue-format correction.
Record `SKIPPED` and the reason; skipping is a decision, not silence.

Before generating routes, record a semantic `context_envelope` in the route
manifest. It must identify the complete target block, its preceding and
following logical blocks, earlier definitions/symbols inspected, downstream
occurrences checked, protected anchors, and the applicable abstraction
contract. Do not substitute a fixed line count for this evidence. Do not alter
a protected anchor inside the current route; surface any necessary neighboring
change as explicit additional scope.

The envelope must also contain `reviewer_census` with four visible distinctions:

- `direct_comment_ids`: comments whose requirement and anchor govern the target;
- `inherited_ripple_ids`: earlier comments that constrain consistency here;
- `adjacent_block_comment_ids`: nearby comments that belong to another block and
  must not be misassigned;
- `internal_defect_ids`: `D...` findings discovered locally, never mislabeled
  as reviewer comments.

Support the census with raw-comment/ledger anchors and a bounded conclusion.
Write empty arrays explicitly. “No direct comments” does not imply “no defect.”
Do not claim completeness unless every reviewer source in the preflight
manifest was available and inspected.

## 2. Permitted route types

Generate one route when the correction is forced by evidence. Generate two or
three only when they are genuinely different strategies; never manufacture
cosmetic alternatives.

| Type | Use when |
| --- | --- |
| `CLAIM_CALIBRATION` | Existing evidence supports a narrower or more precise claim. |
| `THEORY_REPAIR` | The model, derivation, assumptions, or technical explanation must change. |
| `EVIDENCE_REPAIR` | A parameter, experiment, analysis, baseline, figure, citation, or reproducibility item must be added or rerun. |
| `SCOPE_REMOVAL` | The criticized element and every dependent claim/artifact should be removed. |
| `EVIDENCE_REBUTTAL` | Existing direct evidence supports declining the requested change. |
| `HUMAN_DECISION` | A material scientific, authorship, scope, cost, or risk choice cannot be inferred safely. |

## 3. Route criteria

Evaluate every proposed route against all criteria. Use only `PASS`, `PARTIAL`,
`FAIL`, `NOT_APPLICABLE`, or `UNVERIFIABLE`; do not calculate totals or averages.

| ID | Criterion | Primary evaluator |
| --- | --- | --- |
| `RG1` | **Reviewer coverage:** the route satisfies the scientific task objective or exact reviewer requirement, not a nearby issue. | `project` for current requirement; `writing` for explicit rhetorical coverage; local agent decides. |
| `RG2` | **Scientific support:** every technical proposition is established by inspected evidence or explicitly marked as an inference/unknown. | `theory` plus local primary evidence. |
| `RG3` | **Internal consistency:** equations, definitions, assumptions, dimensions, notation, abstraction level, and implementation remain mutually consistent. | `theory` plus local repository checks. |
| `RG4` | **Scope and claim strength:** novelty, generality, causality, stability, and performance language do not exceed the evidence or section purpose. | `writing`, informed by `theory` where meaning is technical. |
| `RG5` | **Ripple closure:** every affected earlier/later section, caption, table, figure, citation, result, conclusion, ledger, and response-letter statement is named. | `project` plus local cross-version search. |
| `RG6` | **Evidence burden and reproducibility:** required new data, computation, citation, parameter, or experiment is explicit and feasible; no missing work is disguised as prose. | `theory` and local experiment/code evidence. |
| `RG7` | **Binary verifiability:** the route has observable acceptance checks that can prove completion. | Relevant expert notebook plus local agent. |
| `RG8` | **Minimality and reversibility:** the route is the smallest coherent change and avoids unrelated rewriting. | `writing` plus local diff review. |
| `RG9` | **Authority boundary:** the route does not invent author intent, experimental facts, reviewer intent, or permission for new work; material choices are surfaced to the user. | `project` plus local agent. |

`RG1`, `RG2`, `RG3`, and `RG7` are hard gates. A route with any outcome other
than `PASS` on a hard gate cannot be `RECOMMENDED` or `VIABLE`. `RG8` can break a
tie only after scientific and evidentiary requirements pass; brevity never
overrides validity.

If the requested objective itself exceeds the evidence, do not silently redefine
it and mark `RG1` as `PASS`. For example, nominal simulations cannot support a
requested universal robust-stability guarantee. A route reporting only those
observations may be scientifically sound but remains `NEEDS_HUMAN_DECISION`
with `RG1=PARTIAL` until the author accepts the narrower objective. If missing
proof/data leaves no defensible route, record `BLOCKED` and name that missing
evidence. This is distinct from a failed required notebook consultation.

## 4. Selective NotebookLM allocation

NotebookLM is advisory and source-grounded. It does not select the final route.
Perform the consultation steps below only when the user, grounding need, or
applicable project policy requires them. Otherwise record justified local
`NOT_REQUIRED` evaluation with inspected evidence and no query IDs/attribution.
Apply the author's configured source-scope policy for the current project.

1. **Project context, once:** when reviewer history or ripple context matters,
   validate the project snapshot and recover `RG1`, `RG5`, and `RG9` constraints.
2. **Independent expert pass:** query `theory` against the relevant domain sources
   for technical routes (`RG2`, `RG3`, technical `RG6`/`RG7`) and `writing` for
   rhetorical/scope alternatives (`RG1`, `RG4`, rhetorical `RG7`, `RG8`). Run
   both concurrently only when both domains are genuinely implicated. Require
   `theory` to report which sources it actually used. Resolve the `writing`
   source set with `writing_source_router.py`; do not select its whole library.
   Describe routes neutrally and in non-preferential order. Before either query,
   validate its prompt, repeating `--route` for every route under review:

   ```powershell
   & $python paper-revision/scripts/notebooklm_receipt_guard.py `
     --check-prompt <prompt.txt> --phase route --role <theory|writing> `
     --route R-A --route R-B --pretty
   ```

   A route prompt may request an output schema and allowed outcome vocabulary,
   but it must not contain expected outcome rows, a preferred route, a
   `recommended` label, or concrete conclusions such as `MISSING_EVIDENCE:
   NONE`. Those fields must be placeholders until NotebookLM answers.
3. **Local matrix:** the agent combines notebook evidence with the current
   repository and records a route decision manifest. Save the exact prompt and
   raw wrapper JSON for each completed query; a narrated result is insufficient.
4. **Targeted refinement, optional:** if exactly one criterion remains
   `PARTIAL` or `UNVERIFIABLE`, ask only the notebook capable of resolving that
   criterion. A theory refinement may use only the source IDs identified in the
   first pass when its recorded purpose is to verify a critical proposition or
   resolve a documented conflict. Do not restart all three queries.

The route phase permits at most **two rounds**. Round 1 is the independent
specialist pass; round 2 is one targeted refinement. If a hard gate still does
not pass, finish as `BLOCKED` or `NEEDS_HUMAN_DECISION`. Repetition is not
convergence.

Prompt and output paths are append-only audit records. Never rewrite a prompt
after it was sent and never use `--overwrite-output` for route evidence. If a
query or output contract is malformed, retain that failed attempt and create a
new query ID, prompt file, and output file for the permitted next round. A
corrected prompt may clarify labels or criteria, but it still cannot prescribe
the answer.

The `project` notebook brackets the workflow; it is not a third expert vote. A
final project-consistency query occurs only after the selected route has been
implemented and locally verified.

## 5. Selection rule

Choose lexicographically, not by weighted score:

1. reject routes that fail a hard gate;
2. reject routes that contradict current primary evidence;
3. surface routes requiring unapproved experiments, scope changes, unsupported
   rebuttals, or authorship judgments as `NEEDS_HUMAN_DECISION`;
4. among the remaining routes, prefer complete ripple closure, then smaller
   evidence burden, then minimality/reversibility;
5. select exactly one `RECOMMENDED` route or select none.

The local recommendation is advisory. For ready routes, record
`AWAITING_USER_APPROVAL`, present the route comparison in chat, and stop. If no
route is ready, record `NEEDS_HUMAN_DECISION` or `BLOCKED`, explain the unresolved
objective or missing evidence, and do not request approval of an invalid route. User
approval is required before drafting the final replacement text for every route
covered by this gate—not only routes that change contribution scope. The user
may approve a `RECOMMENDED` or `VIABLE` route; selecting a route does not approve
the later manuscript wording.

## 6. Required artifact and validation

Write the decision to a JSON file using
`route-decision.example.json` as the schema example. Validate it before drafting
or applying the patch:

```powershell
& $python paper-revision/scripts/notebooklm_receipt_guard.py `
  route-decision.json --pretty
& $python paper-revision/scripts/route_guard.py route-decision.json --pretty
```

The files under `references/receipt-examples/` are synthetic offline fixtures
for validating the schema. Their `example-*` notebook/source IDs and findings
must never be copied into a real project decision.

For each completed NotebookLM role, `notebooklm_consultation.receipts` binds a
stable query ID to the exact prompt file, raw wrapper output, resolved notebook
ID, source IDs, and output SHA-256. The guard checks the wrapper schema,
individually successful result (including a successful query in a partial batch), prompt hash, source scope, required answer labels, and route
IDs. It also rejects prompts that seed outcomes or recommendations and output
paths with archived predecessors created by an overwrite. The direct wrapper
fallback ID `single` is not admissible evidence.
The sibling `notebooklm_consultation.findings` array records each theory/writing
`route_id | criterion_id | outcome` triplet with its query ID. The guard requires
that exact triplet to occur in the raw answer and requires complete specialist
coverage (`RG2/RG3/RG6/RG7` for theory; `RG1/RG4/RG7/RG8` for writing) for every
route sent to that role.

`AWAITING_USER_APPROVAL`, `SELECTED`, and `NEEDS_HUMAN_DECISION` require a
completed, valid receipt set for every declared required role when consultation
is required. A justified local evaluation may use `NOT_REQUIRED` with empty
roles, receipts, findings, and query IDs only when the skill/project policy
permits it. Record the inspected local evidence for all criteria. Unavailable
required consultation is `BLOCKED`, never a local waiver. If a required
NotebookLM query fails or its artifact is missing, use `BLOCKED`. Local analysis
may still be shown as `LOCAL_PROVISIONAL`, but it may not be labeled as a
NotebookLM verdict and is not an evaluated route handoff.

A scientific blockage found wholly from local evidence may use selection
`BLOCKED` with consultation `NOT_REQUIRED` only when consultation is genuinely
unnecessary under policy. Record the inspected evidence, blocking reason and
selection basis; leave required roles, receipts, findings and query IDs empty.
No route is selected and no candidate application is authorized. Never use this
combination to disguise failure of a required notebook or missing receipt.

Allowed selection states are:

- `AWAITING_USER_APPROVAL`: evaluated routes and an optional recommendation are
  ready, but no route has been chosen by the user;
- `SELECTED`: the user explicitly chose one `RECOMMENDED` or `VIABLE` route
  after seeing the comparison, and `user_route_decision` records that response;
- `NEEDS_HUMAN_DECISION`: no route is selected and the unresolved choice is
  explicit;
- `BLOCKED`: no defensible route can currently pass;
- `SKIPPED`: the gate was not required, no routes were generated, and the
  deterministic reason is recorded.

When the gate applies, `context_envelope` is mandatory. `SELECTED` is invalid
without `user_route_decision.status=APPROVED`, the approved route ID, and a
non-empty record of the user's response after the route handoff. The agent may
not manufacture this evidence from its own recommendation.

After a route is selected, use the separate manuscript rubric only for the
layers applicable to the resulting text or artifact. Route approval does not
mean the manuscript block passes scientific-writing review.

## 7. Required user-facing route handoff

Do not expose only the JSON manifest. Present a compact readable comparison:

1. **Reviewer census:** direct IDs, inherited ripple IDs, adjacent-block IDs,
   and internal defects, including `NONE` where applicable.
2. **Diagnosis:** exact problem, evidence, severity, affected locations, and
   the bounded scope of the audit.
3. **Consultation receipt:** notebook role, stable query ID, what was asked,
   selected source scope, and success/block state.
4. **Route A/B/C:** what changes, the applicable `RG` criterion, evaluator,
   `PASS/PARTIAL/FAIL/NOT_APPLICABLE/UNVERIFIABLE`, evidence/query ID, main
   benefit, work required, risk, and ripple effects.
5. **Recommendation:** the local recommendation and its evidence-based reason;
   do not present it as the user's decision.
6. **Decision requested:** ask the user to choose, modify, or reject a route.

Use this minimum chat shape so the author can audit the decision without opening
JSON or LaTeX:

```markdown
Reviewer census
- Direct: C1 (or NONE)
- Inherited ripple: R8, C24 (or NONE)
- Adjacent block: C14 (or NONE)
- Internal defects: D1, D2 (or NONE)

Notebook consultations
| Role | Query ID | What was asked | Source scope | Receipt |
| project/theory/writing | stable ID | one-line question | exact IDs or ALL_ENABLED_THEORY | VERIFIED/BLOCKED |

Route evidence
| Route | RG criterion | Evaluator | Outcome | Evidence / query ID |
| R-A | RG2 | theory | PASS | C1-theory-route-r1: bounded support |

Route comparison
| Route | Proposed strategy | Benefit | Work/evidence | Risk | Ripple targets |
```

After the tables, state the local recommendation and ask for a route choice.
The exact replacement paragraph/equation belongs to the later draft gate and
must not appear here.

End the turn there. Do not include final replacement prose, modify the `.tex`,
compile, commit, or push while the state is `AWAITING_USER_APPROVAL`.
