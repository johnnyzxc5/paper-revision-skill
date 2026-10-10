# Section writing guide

Read only the heading needed for the current block, plus the editorial contract
and applicable rubric layers. These are drafting heuristics, not venue rules or
mandatory section names. Keep outlines, claim maps, paragraph-role labels, and
audit questions in author-side notes. Present manuscript candidates using the
existing exact LaTeX output contract.

## Title and abstract

Name the actual problem and supported scope. In the abstract, connect need,
approach, decisive evidence, and bounded answer. Include verified quantitative
results when useful; never invent a number to complete a template. Identify
formal results as formal and observations as empirical. Check every claim and
number against the body. Define essential terms for independent readability;
omit implementation detail that does not change interpretation.

## Introduction

Establish the problem, why it matters, and the specific unresolved question.
Position the answer against inspected closest work. State contributions as
deliverables with their evidence and scope; do not inflate incremental work or
force novelty terminology. Give enough prerequisites to understand the question
without importing the full method. Keep a roadmap only when it helps navigation.

## Related work

Group sources by the technical distinction relevant to the claim: assumptions,
information requirements, sensing/actuation, guarantees, or evaluation conditions.
Explain what the comparison permits the reader to conclude. Verify each citation
supports the attributed statement; metadata verification is insufficient. Avoid
paper-by-paper catalogs and unsupported claims of exhaustive coverage.

## Preliminaries and theory

Introduce only concepts needed by dependent results. State domains, dimensions,
assumptions, and mathematical conventions at their point of use. Separate theorem,
derivation, approximation, and heuristic. Explain what a result means for the
system and trace proof dependencies. Preserve quantifiers and distinguish
open-loop properties from closed-loop guarantees.

## Method

Move from the scientific principle to the ordered formulation, inputs, outputs,
and operations. Explain design choices where they affect interpretation. Keep
general mechanics separate from platform, solver, fault case, and parameter
instantiation. Match the inspected implementation and preserve details needed for
the claimed reproducibility. Do not add an advantage without supporting evidence.

## Experimental setup and results

Define the tested question, system/data, conditions, comparator, metric, and
protocol before the result needs them. Report observations with units, aggregation,
denominators, and applicable uncertainty. Explain what figures and tables establish
instead of repeating every value. State which evidence is simulated, measured,
representative, or aggregate; retain failures that change the inference.

## Discussion and conclusion

Interpret the supported answer, plausible mechanisms, material limitations, and
practical implications. Separate direct findings from explanations and future
work. Keep the conclusion aligned with the original problem and demonstrated
scope; introduce neither new evidence nor an expanded guarantee. Acknowledge an
unresolved question where it changes the answer, without adding defensive caveats
about tasks the paper never claimed.

## Response letter

For each actual reviewer item, retain its ID and faithful requirement, give the
scientific answer, then identify the applied change and stable manuscript
location, or explain a supported rebuttal. Distinguish work completed from work
proposed or deferred, and state any remaining limitation material to the answer.
Route approval alone does not justify saying a correction was implemented or the
comment resolved. Use the canonical ledger's current evidence, not an old summary.

Design provenance: [design-sources.md](design-sources.md).
