# Scientific writing contract

## Contents

1. Deliverable and evidence
2. Manuscript rhetoric
3. Minimum sufficient exposition
4. Redundancy and information flow
5. Notation and acronyms
6. Section purpose and claim strength
7. Local editorial acceptance
8. Materiality and stopping

## 1. Deliverable and evidence

Declare `MANUSCRIPT`, `RESPONSE_LETTER`, or `AUDIT_NOTES` before writing.

| Deliverable | Write | Keep elsewhere |
| --- | --- | --- |
| MANUSCRIPT | Scientific problem, definitions, method, reasoning, evidence, interpretation, and material limitations. | Reviewer IDs, change history, audit verdicts, approval records, or explanations of the revision process. |
| RESPONSE_LETTER | Faithful reviewer requirement, scientific answer, applied change with an anchor, or evidence-based rebuttal. | Unsupported claims of completion or statements that a proposed change has already been applied. |
| AUDIT_NOTES | Defects, evidence, alternatives, checks, uncertainty, and author decisions. | New assertions presented as established manuscript facts. |

Translate a reviewer comment into a scientific need before drafting: a missing
definition, assumption, justification, procedure, comparison, or claim boundary.
Record that mapping in notes. Satisfy the need in the manuscript without making
the reviewer its addressee. For Compose/Edit, derive acceptance from the author's
objective and section purpose; do not invent reviewer context.

Treat the current manuscript as evidence of what it says, not proof that its
claims are correct. Preserve the distinction between inspected results, cited
theory, source-grounded inference, and an unresolved fact. Never fill a missing
proof, experiment, definition, or parameter with confident prose.

## 2. Manuscript rhetoric

State what the method does, how it works, and under which conditions. Use
affirmative descriptions of scope when they communicate it precisely. Do not
add defensive lists of capabilities the study never claims merely to reassure
a reviewer. Retain a negative distinction when it changes a reader's scientific
interpretation or supports a relevant comparison.

Use the reader test: if the reader did not know the revision history, would this
sentence still help explain or evaluate the study? Move sentences whose sole
purpose is to demonstrate a correction to the response letter or audit notes.

Illustrative scope example; use only if the evidence actually supports it:

- Avoid a defensive chain: “The classifier does not localize the fault and does
  not estimate its location.”
- State the supported task: “The classifier identifies the fault type from
  measurements at a specified port.”
- If localization affects the interpretation of results, retain one precise
  limitation in the appropriate method or discussion passage.

Remove empty metadiscourse, duplicated previews, and revision commentary such as
“to address this concern” or “we have now clarified” from MANUSCRIPT. Keep a
short roadmap or cross-reference only when it performs useful navigation.
Do not enforce banned-word replacement without judging context.

## 3. Minimum sufficient exposition

For each sentence identify its contribution: definition, assumption, procedure,
justification, observation, interpretation, material qualification, or necessary
logical connection. Remove or merge it when it contributes no needed information.

Prefer the shortest formulation that preserves:

- the mathematical statement, quantifiers, dimensions, and validity conditions;
- the causal or logical steps needed to understand the argument;
- the method details needed for the claimed reproducibility;
- the evidence and limitations needed to interpret a result.

Do not optimize a word-count reduction or quality score. Do not delete a useful
equation explanation just because it follows an equation. Do not add explanations
of routine algebra when the intended reader can follow it directly.

Use precise academic language, concrete technical actors, consistent terminology,
and evidence-appropriate verbs. Allow passive voice when it improves information
flow or the actor is irrelevant. Avoid promotional emphasis, ornamental
synonyms, and nominalizations that obscure the mechanism.

## 4. Redundancy and information flow

Before editing, record a compact context envelope:

- `INHERITED_INFORMATION`: definitions and propositions already established;
- `NEW_INFORMATION`: what this block must contribute;
- `FOLLOWING_BLOCK_PURPOSE`: what should remain for the next block;
- `REQUIRED_CROSS_REFERENCES`: anchors necessary for reading continuity.

Inspect the complete target block, its controlling neighbors, earlier
definitions, and material later dependencies. Search for equivalent propositions,
not only repeated wording. If a concept has already been explained adequately,
reuse it and reference its anchor when helpful; do not re-teach it.
Perform this continuity/redundancy check locally with the current manuscript;
a writing notebook need not receive a paper skeleton. For a source-based block
review, record the controlling context and exact-candidate local checks in
[writing-block-review.md](writing-block-review.md).

Allow brief recapitulation where the section's purpose changes: the abstract is
self-contained, the introduction positions contributions, and the conclusion
answers the problem. Do not mechanically delete these functional recurrences.

Organize paragraphs around one dominant scientific function. Express actual
logical relations in transitions. Prefer direct entry into a formal block when
a preceding preview would only repeat its content.

## 5. Notation and acronyms

Read the current project registers and verify entries against the manuscript.
Use `manuscript-registry.example.json` if no register exists; existing equivalent
registers may be retained. A register is a navigation aid, not independent proof.

For each new symbol or operator, specify its meaning and its domain or dimension
when needed for interpretation. Introduce it before dependent use or in the same
grammatical equation sentence with an immediate “where” clause. For example,
introduce the physical quantity before the equation and define its parameters
immediately afterward. Do not require awkward advance prose for every bound
index or standard operator, but make indexing and material conventions explicit.

Preserve established symbols and macros. Check the full notation before creating
a local shorthand; do not reuse a symbol for a conflicting role. Keep scalar,
vector, matrix, transpose, estimate, and time-dependence conventions consistent.
Record a proposed renaming and its propagation; it is a separate scope change.

Define an acronym at its first occurrence in the applicable scope, then use its
short form consistently. Do not expand it again in that scope as if it were new.
Treat abstract and body as distinct scopes when venue requirements or independent
readability require it; define separate caption or supplement scopes only when
justified. Do not introduce an acronym used only once unless it is necessary.

Maintain one canonical technical term per concept. Avoid swapping terminology
for variety. Update registers only from verified accepted manuscript state.
Do not silently change a mathematical meaning to improve a sentence.

## 6. Section purpose and claim strength

Apply the section-purpose table in the scientific rubric and the project profile
when one exists. Keep general formulation distinct from case-study choices.
Introduce prerequisites before results and avoid importing implementation details
into a general-method explanation without a scientific reason.

Distinguish a formal guarantee, derivation, approximation, empirical observation,
and hypothesis. Preserve the conditions of stability, causality, robustness,
generality, novelty, and comparative performance claims. A writing edit cannot
upgrade the level of evidence.

When replacing an unsupported claim, check the new proposition as well as the
removed words: an alternative causal mechanism, necessity claim or explanation
needs its own support. Use [claim-history.md](claim-history.md) when a material
claim is withdrawn or limited. This is semantic review, not banned-word matching.
Compare the scientific propositions before and after polishing: object evaluated,
conditions, comparator, unit/denominator, uncertainty and unresolved limits.
Unchanged numbers are insufficient. Treat manual/model examples as editorial
suggestions, never as experiment-specific mechanisms or results. Record material
replacement claims and their existing evidence in the exact-block local review.

Report material limitations where they affect interpretation; place future work
where the section purpose supports it. Do not add hypothetical limitations or
irrelevant “does not” statements solely as defensive protection.

## 7. Local editorial acceptance

Check the candidate against these stable criteria, using PASS, FAIL, or a named
unresolved dependency. Report only defects and decisions the author needs:

| ID | Acceptance check |
| --- | --- |
| EW1 | The declared deliverable uses its own rhetoric; MANUSCRIPT contains no revision-response leakage. |
| EW2 | Every retained sentence contributes necessary scientific information or navigation. |
| EW3 | Necessary assumptions, reasoning, evidence, and reproducibility details survive shortening. |
| EW4 | Explanations do not unnecessarily repeat inherited or downstream material. |
| EW5 | New symbols are introduced with material meaning/dimension; existing notation remains consistent. |
| EW6 | Acronyms are defined once per justified scope and then used consistently. |
| EW7 | Technical terminology, section abstraction, and evidence-calibrated claims are preserved. |
| EW8 | Material limitations remain explicit without irrelevant defensive caveats. |
| EW9 | Replacement claims have support within their stated scope and do not reintroduce a withdrawn inference through different wording. |

Use these as author-side operational checks. They require no invented book
citation. Attribute an external normative rule to its actual source, and verify
IEEE requirements only when the target venue activates them.

## 8. Materiality and stopping

Review for scientific adequacy and reader understanding, not perfect wording.
Before acting on a finding, verify its exact anchor in the original and classify it:

- **MATERIAL:** an incorrect result, unsupported claim, changed denominator or
  uncertainty, missing reasoning, consequential ambiguity, or actual syntax/layout
  failure. Correct it within scope; consult again only if a material question remains
  or a required exact-candidate audit needs refreshing after an accepted change.
- **OPTIONAL:** a defensible wording alternative, punctuation, preferred number
  formatting, or other polish that preserves meaning and comprehension. Report only
  when useful; it does not block acceptance or justify another consultation.
- **DISMISSED:** absent from the original, introduced by source conversion, or
  based on an unsupported style rule. Record a short reason and do not edit the
  manuscript to satisfy it.

Do not accept a finding's severity merely because a model calls it critical.
Treat a venue rule as mandatory only with an applicable, inspected primary basis.
For each retained defect, explain what scientific interpretation, reader
understanding, reproducibility or actual operation would change if left unresolved.

Close once material issues are resolved and the argument is understandable. Leave
optional polish for author choice; do not manufacture defects to fill a rubric or
reopen accepted blocks. A second audit round is a ceiling, not a target.
When the author asks to keep the adequate wording, do not apply optional edits
that would themselves require another candidate and audit.

Keep scientific readiness separate from consultation validity. Useful observations
from an imperfect consultation may inform a locally checked assessment, with their
scope stated honestly. Formatting-only source alterations do not invalidate every
argumentative observation, but neither a pasted hash nor useful advice establishes
an exact-source PASS. Do not repeat a consultation solely to obtain a ceremonial
verdict or fix bookkeeping; do not waive a material scientific uncertainty or a
required exact-text application check. Explain a necessary dependency briefly,
without returning an internal procedure for the author to execute.
