# Evidence-led drafting

Use for Compose, substantive Edit, or an approved restructure. This is an
author-side planning aid; it adds no approval gate. The scope, route/draft gates,
NotebookLM routing, exact candidate format, and editorial contract in `SKILL.md`
remain authoritative. During Route, plan alternatives without drafting final
replacement prose. Load only the relevant heading in
[section-writing-guide.md](section-writing-guide.md).

## Establish the argument

Inspect available results, proofs, figures, tables, code/configuration, and
primary literature before composing claims. Record the problem, intended reader,
supported answer, and material boundary in a few sentences. Distinguish an
established literature gap from an author hypothesis; do not manufacture novelty
or imply that an unsearched literature is absent.

State the scientific question and contribution in terms appropriate to this
paper's reader. Distinguish established background, the proposed method and its
selected realization. Use this distinction to place material, not to impose a
fixed section order. A design requirement of the proposed method needs an
explicit rationale; it is not a theorem that every competing method must satisfy.

Maintain a compact claim map for central, comparative, quantitative, and
scope-sensitive statements:

| Field | Record |
| --- | --- |
| Claim | Exact proposition and kind: formal, empirical, interpretation, or hypothesis. |
| Evidence locator | Stable theorem/proof, file and label, figure/table and metric, data/configuration, or primary source and passage. |
| Support boundary | Assumptions, quantifiers, systems, conditions, comparator, metric, and uncertainty material to this claim. |
| Verification state | `VERIFIED`, `PARTIAL`, `UNVERIFIABLE`, or `CONTRADICTED`, with one reason. |

These states describe evidence verification, not reviewer progress. A locator
alone earns no `VERIFIED` status: inspect whether it supports the proposition
within its stated boundary. Missing evidence stays in notes as a dependency;
omit or qualify unsupported prose without inventing data, citations, or proofs.

A theorem requires the actual statement, hypotheses, and proof/source checks.
Simulation or hardware trajectories cannot establish a formal stability or
convergence guarantee. Empirical comparisons require the inspected metric,
comparator, protocol, aggregation, and uncertainty appropriate to the inference;
a small tracking error cannot establish general robustness. A proposed physical
mechanism remains interpretation unless the evidence discriminates it from
plausible alternatives.

## Choose an architecture

Use the evidence and venue to choose structure; do not force IMRAD, a fixed
number of contributions, or an empirical comparison into every paper.

- **Theory led:** motivate the question; introduce prerequisites and assumptions;
  state the principal result; explain its mechanism and proof dependencies;
  place consequences and illustrative validation where they help interpretation.
  Keep hypotheses visible even when full proofs belong in an appendix.
- **Empirical:** define the problem and method; provide the setup needed to read
  the principal observation; present the decisive comparison; examine mechanism,
  sensitivity, and limitations when supported. Separate simulation from hardware
  evidence and representative trajectories from aggregates.
- **Mixed:** identify which conclusions follow from proof and which from measured
  behavior. Connect them explicitly without letting one substitute for the other.

For each in-scope section, make a mini-outline: reader question, answer, needed
prerequisites, evidence anchors, and paragraph jobs. Reuse inherited information
and existing notation. Draft outward from the strongest inspected evidence;
stabilize the title and abstract after the claim hierarchy, when they are in
scope. An outline is internal preparation, not a new approval request or a
replacement for the authoritative LaTeX candidate.

Within a technical passage, establish the quantity or operation's purpose, its
inputs and assumptions, the defining relation, and the interpretation needed for
its next use. Introduce each necessary term once; connect successive expressions
by stating whether they are definitions, substitutions, approximations or special
cases. Use an extra equation or symbol only when it makes that relationship
clearer. The order may vary with the argument; this is not a paragraph template.

For quantitative prose, identify the observation unit, denominator, grouping,
aggregation, conditions and comparator before interpreting a number. Repeated
measurements or variants of one parent are not automatically independent units;
state the actual design and limits without importing another paper's split or
statistical procedure. Use only synthetic examples or author-approved historical
cases, stating their evidence boundary.

## Verify flow and stop

Reverse outline the exact candidate: summarize each paragraph's contribution in
one line, then connect it to the section answer and its support. Fix missing
reasoning, duplicate functions, misplaced detail, and claims without support.
Preserve useful recapitulation that serves a different section purpose.

Run a focused skeptical check: could a qualified reader misread the scope,
reproduce the claimed procedure, locate support, or identify an unresolved
alternative? Distinguish evidence repair from prose repair. Apply only relevant
rubric/editorial checks and inspect named dependencies. Stop when those checks
pass or a concrete evidence/author decision remains. Do not chase stylistic
perfection, numeric scores, or repeat audits of unchanged passing text; respect
the existing two-round specialist limits and human waiting states.

Design provenance: [design-sources.md](design-sources.md).
