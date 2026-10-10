# Technical Scientific Paper Revision Rubric

**Source title:** Technical Scientific Paper Revision Rubric v1.1  
**Content version:** 1.1; synchronize the remote source against this file's hash  
**Source role:** Operational evaluation schema for author-side revision  
**Scope:** scientific manuscripts; domain-specific checks apply only when relevant  
**Venue profile:** IEEE when the IEEE annex is explicitly activated

This rubric is both an internal reference for the `paper-revision`
skill and a standalone source that may be uploaded to NotebookLM. It organizes
questions and evidence; it is not an official IEEE document and does not
override primary sources.

For exact-text review, identify the complete candidate, its version and the
actually covered blocks. General guidance cannot certify text it was not asked
to inspect. Source presence/processing and a successful query do not establish
full review or scientific correctness. Continuity with other sections and global
redundancy are checked locally by the manuscript agent; no paper skeleton source
is required or uploaded for this workflow.

When polishing, check replacement propositions as well as removed wording.
Preserve the evaluated object, conditions, comparators, metric denominators,
uncertainty and unresolved differences. Writing examples cannot establish a new
mechanism, physical interpretation, equivalence tolerance or deployment outcome.

### Portable author-side acceptance checks

These EW definitions also appear in the local editorial contract so the uploaded
rubric is self-contained. Keep both definitions synchronized when changing them.
They are operational criteria, not official venue rules or scientific proof.
The local agent checks paper-wide continuity/redundancy; a writing review uses
only the target and explicitly supplied dependency context.

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

## 1. Authority and evidence order

Resolve conflicts in this order:

1. current instructions and template of the target journal or conference;
2. current official policies, style manuals, standards, and primary technical
   sources;
3. current manuscript, experiment code, data, figures, and reviewer wording;
4. this operational rubric;
5. general writing heuristics and model recommendations.

An instruction containing *may*, *usually*, or *should* must not be converted
into an absolute requirement. When the primary source is unavailable or the
applicable venue is unknown, report `UNVERIFIABLE` instead of inventing a rule.

## 2. Assessment vocabulary

### Criterion outcome

| Outcome | Meaning |
| --- | --- |
| `PASS` | Direct evidence satisfies the criterion. |
| `PARTIAL` | Some evidence passes; a precise gap remains. |
| `FAIL` | Direct evidence contradicts or omits the criterion. |
| `NOT_APPLICABLE` | The criterion does not apply to this study or section. |
| `UNVERIFIABLE` | A named source, artifact, or scientific fact is missing. |

### Defect severity

Severity is independent of reviewer-item progress status.

| Severity | Meaning |
| --- | --- |
| `BLOCKER` | Validity cannot be established without new evidence, data, analysis, or a material scientific decision. Wording alone cannot close it. |
| `MAJOR` | Technical meaning, reproducibility, interpretation, or a central claim is materially affected, but the available work may permit repair. |
| `MINOR` | A localized clarity or consistency defect does not change the scientific conclusion. |
| `EDITORIAL` | Mechanical venue, grammar, typography, or formatting defect. |

The author-side agent never announces acceptance, rejection, fraud, or
misconduct. It reports evidence and uses `BLOCKER` or `NEEDS_DECISION`; the
editor or responsible human makes the decision.

### Evidence label

- `OBSERVED`: directly present in an inspected artifact.
- `INFERRED`: reasoned from observed evidence but not explicitly stated.
- `PROPOSED`: a candidate correction not yet applied or verified.

## 3. Core rubric

### L0 — Review boundary and evidence manifest

**Evidence:** target venue and article type; current manuscript; bibliography;
figures/tables; relevant data and code; raw reviewer comments; old version when
comparison is requested.

**Pass checks:**

- The task phase is explicit: audit/diagnose, route, draft/preview, apply, or
  resume.
- The active manuscript version and target venue are identified.
- Missing artifacts and resulting limitations are named.
- Claims of completeness are bounded by the inspected material.

Use `UNVERIFIABLE` when a required artifact is absent. Do not call an audit
exhaustive merely because the available files were searched exhaustively.

### L1 — Scope, problem, novelty, and contribution

**Evidence:** title, abstract, introduction, related work, contribution list,
discussion, conclusion, and the literature cited for novelty.

**Pass checks:**

- The problem and practical or scientific need are explicit.
- The target venue and claimed contribution are aligned.
- Each novelty claim is distinguished from the closest prior work.
- Contributions state what is delivered, under which assumptions, and with
  what evidence.
- Scope and limitations are consistent from title through conclusion.
- Promotional terms such as *novel*, *general*, *robust*, *significant*, and
  *state of the art* have an explicit comparison or proof basis.

Potential severity: `BLOCKER` for an unverifiable central novelty claim;
`MAJOR` for scope drift or unsupported contribution boundaries; `MINOR` for a
localized positioning defect.

### L2 — Theory, mathematics, and physical consistency

**Evidence:** definitions, assumptions, equations, derivations, proofs,
notation, units, cited theory, and numerical implementation of the model.

**Pass checks:**

- Every symbol, set, index, state, input, output, parameter, and operator is
  defined before use with its domain or dimension when material.
- Assumptions are explicit, necessary, internally consistent, and propagated
  to claims and conclusions.
- Algebra, signs, dimensions, units, boundary conditions, and equation
  dependencies are consistent.
- Formal results distinguish theorem, derivation, approximation, heuristic,
  numerical observation, and empirical evidence.
- Stability, convergence, optimality, identifiability, observability,
  causality, and invariance claims state their hypotheses and proof boundary.
- Limiting cases and degenerate cases do not contradict the formulation.
- The implemented equations match the reported mathematical model.

Potential severity: `BLOCKER` for a false central equation, missing proof or
assumption needed for the main claim, or dimensional inconsistency that changes
the method; `MAJOR` for repairable derivation or notation defects; `EDITORIAL`
for typography only.

#### Control and robotics checks when applicable

- State, configuration, momentum, input, disturbance, and measured output
  spaces are unambiguous.
- Actuation, colocation, sensing, topology, and model-knowledge assumptions are
  explicit.
- Open-loop properties are not presented as closed-loop guarantees.
- Empirically bounded tracking is not called Lyapunov, ISS, or asymptotic
  stability without the corresponding result.
- Fault, uncertainty, noise, and disturbance channels are separated unless a
  stated model intentionally couples them.
- Constraint satisfaction and recursive feasibility are not claimed from a
  design margin alone.

### L3 — Method and reproducibility

**Evidence:** methodology, algorithms, configurations, code, hardware/software
versions, datasets, parameter tables, and preprocessing pipeline.

**Pass checks:**

- An independent qualified reader could reconstruct the full processing and
  experimental sequence.
- All parameters affecting reported results are declared or linked to a stable
  artifact.
- Algorithm inputs, outputs, initialization, stopping rules, and selection
  policies are stated.
- Software, solver, tolerance, sampling, hardware, and randomization details
  are sufficient for the claimed level of reproducibility.
- The description matches the inspected code and configuration.
- Data and code availability statements match actual availability and venue
  requirements; no repository deposit is presumed mandatory without a source.

Potential severity: `BLOCKER` when the method cannot be evaluated or reproduced
from any available artifact; `MAJOR` for missing influential parameters;
`MINOR` for nonessential implementation detail.

### L4 — Experimental design and data integrity

**Evidence:** datasets, acquisition protocol, sample construction, train/valid/
test splits, baselines, ablations, controls, repetitions, and statistical plan.

**Pass checks:**

- The experiment tests the stated research question rather than a proxy left
  unexplained.
- Sample units, counts, inclusion criteria, independence assumptions, and
  denominators are explicit.
- Splits prevent subject, trajectory, temporal, augmentation, or preprocessing
  leakage as applicable.
- Baselines are relevant and compared under defensible conditions; absence of a
  baseline is judged against the contribution, not treated as an automatic
  failure.
- Ablations isolate causal architectural or preprocessing claims when those
  claims are made.
- Repetitions, seeds, uncertainty, and statistical tests match the variability
  and inferential claims.
- Simulation-only, hardware, and real-world evidence are never conflated.

Potential severity: `BLOCKER` for leakage or a design that cannot test the main
claim; `MAJOR` for unfair comparisons or missing uncertainty; `MINOR` for a
clarification that does not change interpretation.

#### Signal-processing checks when applicable

- Sampling rate, bandwidth, anti-aliasing, window duration, overlap, boundary
  treatment, normalization, and filtering are specified.
- Transform family, parameterization, scale/frequency mapping, discretization,
  and image resizing are reproducible.
- Spectral or time-frequency interpretations respect the closed-loop system,
  finite observation window, and transform limitations.

#### Machine-learning checks when applicable

- Class construction, imbalance handling, augmentation, preprocessing fitting,
  checkpoint selection, and hyperparameters are explicit.
- Preprocessing and feature selection are fitted without test-set access.
- Model comparisons separate architecture, capacity, training budget, and data
  availability effects.
- Embeddings and visualizations such as t-SNE are not treated as quantitative
  proof of separability or preserved global distance.

### L5 — Results, statistics, and claim calibration

**Evidence:** tables, figures, captions, metrics, statistical results,
discussion, limitations, and conclusion.

**Pass checks:**

- Metrics, aggregation, averaging, units, denominators, and uncertainty are
  defined.
- Numbers agree across text, tables, figures, abstract, and conclusion.
- Representative samples are labeled as such and not presented as aggregate
  evidence.
- Every causal, comparative, robustness, generalization, or efficiency claim
  has an appropriate experiment, proof, or explicit qualification.
- Statistical significance is separated from effect size and practical
  relevance.
- Negative findings, ambiguity, failure modes, and limitations are reported
  where they affect interpretation.
- Conclusions do not extend beyond the tested systems, faults, operating
  conditions, or data distribution.

Potential severity: `BLOCKER` for fabricated, contradictory, or uninterpretable
central results; `MAJOR` for unsupported causal/general claims; `MINOR` for a
localized reporting inconsistency.

### L6 — Scientific structure and argument

**Evidence:** section order, headings, paragraph sequence, transitions, and
cross-references.

**Pass checks:**

- Each section performs its expected argumentative role.
- Definitions and assumptions precede dependent results.
- General methodology is separated from case-study instantiation.
- Each paragraph has one dominant function and advances the argument.
- Transitions express a real logical relation, not a ceremonial preview.
- Repetition across abstract, introduction, results, and conclusion is limited
  to each section's distinct purpose.
- Later sections do not retain claims contradicted by an earlier revision.
- A revision advances from inherited information to new information without
  re-explaining the preceding block or prematurely resolving the next block.
- Content outside the declared revision scope remains intact unless a separate
  ripple correction is disclosed and approved.

Potential severity: `MAJOR` when organization prevents correct technical
interpretation; `MINOR` for local ordering or transition defects.

### L7 — Scientific prose and rhetorical precision

Apply the author-side `editorial-contract.md` checks EW1-EW9 alongside the
source-grounded prose criteria. Distinguish MANUSCRIPT, RESPONSE_LETTER, and
AUDIT_NOTES. For manuscript revision, convert reviewer feedback into a
scientific need and satisfy it naturally for the reader; do not put revision
history or reviewer-facing explanations in the paper. User style preferences
are operational constraints, not claims of an external normative rule.

**Evidence:** the exact paragraph plus enough preceding and following context to
judge information flow.

**Pass checks:**

- Every sentence defines, claims, justifies, describes, qualifies, contrasts,
  or connects. Preserve the reasoning, assumptions, and material limitations
  required for understanding; do not optimize a word-count reduction. Sentences without a scientific function are removed or merged.
- Established information normally precedes new or cognitively heavy
  information when this improves cohesion.
- Physical or mathematical actors appear near their principal actions; avoid
  nominalizations that hide mechanism or responsibility.
- No fixed word limit is imposed on grammatical subjects. Flag only subjects
  whose length or abstraction delays comprehension of the main verb.
- Passive voice is allowed when the agent is irrelevant or information flow
  benefits. Flag it when it obscures authorship, procedure, or contribution
  ownership.
- Claim verbs match evidence strength: *guarantees* requires formal support;
  *demonstrates* requires direct evidence; *suggests* and *is consistent with*
  do not establish causality.
- Terminology, tense, person, and technical naming remain consistent.
- Equations are integrated into grammatical sentences and interpreted after
  presentation when their significance is not self-evident.
- The expected reader of the section can understand the problem and contribution
  without being assumed to know a niche framework before it is introduced.
- Contribution statements are affirmative and evidence-based. Negative
  comparisons or defensive contrasts appear only when they establish a
  technically relevant distinction supported by evidence.

**Remove or justify:** empty metadiscourse (*it is important to note*, *it is
worth mentioning*, *as can clearly be seen*), promotional adjectives,
duplicated previews, repeated table values without interpretation, and claims
that merely announce section contents.

Potential severity: usually `MINOR`; `MAJOR` when wording changes technical
meaning, hides unsupported causality, or makes contribution ownership
ambiguous.

### L8 — Presentation and venue profile

**Evidence:** target venue instructions, current template, compiled manuscript,
bibliography, figures, tables, and official style sources.

**Pass checks:**

- Notation, acronyms, capitalization, and cross-references are consistent.
  Acronyms are expanded once per justified definition scope, then used
  consistently. Verify abstract/body scope requirements for the actual venue.
- Figures and tables are legible, correctly cited, self-contained enough for
  interpretation, and consistent with the reported data.
- Bibliography entries are complete, nonduplicated, and cited for relevant
  claims.
- Mathematical typography and equation layout follow the active venue profile.
- Layout is verified in the compiled output, not inferred from LaTeX source
  alone.

Potential severity: normally `EDITORIAL`; raise to `MAJOR` when a presentation
defect makes data or mathematics uninterpretable.

### L9 — Integrity, ethics, and conditional compliance

**Evidence:** target venue policies, study type, disclosures, citations, reused
material, data provenance, and applicable ethics approvals.

**Pass checks:**

- Authorship, conflicts, funding, reused material, AI disclosure, and ethics
  statements meet the applicable current policy.
- Sources are cited for borrowed ideas, text, data, figures, and methods.
- Requirements specific to human subjects, animals, clinical trials, safety,
  data deposition, ORCID, or image policies are activated only when the study
  type or venue requires them.
- The agent flags suspicious evidence for responsible human review and never
  declares plagiarism, fabrication, falsification, or misconduct from textual
  similarity alone.

Use `NOT_APPLICABLE` for policies outside the study type. Use `BLOCKER` when an
applicable approval, disclosure, permission, or provenance record is missing.

### L10 — Reviewer response and revision traceability

**Evidence:** raw comment, response letter, old and current manuscript, change
diff, reviewer ledger, and affected downstream sections.

**Pass checks:**

- Each reviewer requirement is preserved faithfully and decomposed into
  testable subrequirements.
- Every response identifies an applied change with a stable manuscript anchor,
  or gives a respectful evidence-based rebuttal.
- Status is derived from the current manuscript, not from the response letter
  or a previous summary.
- Deleted scope is verified across dependent claims, figures, tables,
  comparisons, citations, and filenames.
- Ripple effects are checked backwards and forwards.
- The applied diff preserves equations, lists, definitions, and calibrated
  prose that were outside the approved candidate.
- The response does not claim completion while an acceptance check remains
  open.

Potential severity follows the underlying scientific issue. Evasive wording is
not automatically a `BLOCKER`; failure to address a central validity concern
may be.

## 4. Section-level purpose checks

| Section | Required function |
| --- | --- |
| Title | Identifies the actual topic and scope without unsupported breadth. |
| Abstract | States problem, method, evidence, principal quantitative result when available, and bounded conclusion. |
| Introduction | Establishes need, gap, closest work, contribution, and scope without proving results prematurely. |
| Related work | Organizes comparisons by technical distinction and supports novelty positioning. |
| Preliminaries | Defines only the theory and notation needed later, with assumptions visible. |
| Method | Gives a logically ordered, reproducible formulation at the intended abstraction level. |
| Experimental setup | Declares data, systems, fault/scenario construction, parameters, baselines, splits, and metrics. |
| Results | Reports observations before interpretation and separates representative examples from aggregate evidence. |
| Discussion | Interprets mechanisms, alternatives, limitations, validity threats, and practical meaning. |
| Conclusion | Answers the stated problem without adding new evidence or expanding beyond established scope. |

## 5. IEEE venue annex

Activate this annex only for an IEEE target and check the current publication's
own instructions first.

- Variables are italic. Vectors are bold and follow the paper's declared
  consistent convention. Standard functions and word-based labels in
  subscripts/superscripts are Roman.
- Displayed equations form part of the sentence. A sentence-ending equation
  takes a period; other punctuation follows grammatical need. Conditions are
  separated according to IEEE spacing guidance; no comma precedes `\forall`.
- Use a regular space between a number and its unit. Separate multiplied
  compound units with a centered dot; torque is
  `$\mathrm{N}\,\cdot\,\mathrm{m}$` in LaTeX output, not `Nm`.
- Use a leading zero for decimals. Do not mechanically remove trailing zeros
  from measured results or tables when they express precision or consistent
  reporting; inspect scientific meaning first.
- IEEE examples group tens or hundreds of thousands with spaces and leave a
  four-digit number such as `4000` ungrouped.
- Replacing a complex exponent with `\exp[\cdot]` and replacing an inline
  fraction with `/` are readability options, not universal mandatory rewrites.
- Consecutive reference ranges are permitted, for example `[4]--[7]` in LaTeX
  source when the class renders an en dash. Do not expand them automatically.
- Cite a specific part as in `[3, Fig. 1]`, `[3, eq. (2)]`, or
  `[3, Sec. 4.5]`. Eliminate `ibid.` and `op. cit.`.
- Avoid contractions in technical prose, subject to established technical
  expressions. Apply the spelling convention required by the target venue.
- If an IEEE submission contains the Lena image, flag the current IEEE policy
  for immediate human action. Do not infer image identity solely from a
  filename and do not invent an editorial outcome.

Never apply regex replacements directly to equations, numerical results,
citations, units, or spelling without reviewing the diff in context.

## 6. NotebookLM consumption contract

When this document is used as a NotebookLM source:

1. Use it to select relevant rubric criteria, not as proof that a technical or
   venue-specific claim is true.
2. Cite primary notebook sources for every normative IEEE, mathematical,
   methodological, or rhetorical rule.
3. If the rubric conflicts with a primary source, quote the conflict briefly,
   follow the primary source, and flag the rubric for maintenance.
4. Evaluate only the supplied manuscript text and context. Do not infer local
   files, experiments, reviewer intent, or implementation details.
5. Return criterion-level outcomes and severities, not a numerical score.
6. Distinguish text repair from evidence repair. A polished sentence cannot
   resolve a missing experiment, proof, parameter, citation, or decision.
7. Return `UNVERIFIABLE` when the required evidence or source marker is absent.

Minimum output columns:

```text
CRITERION_ID | OUTCOME | SEVERITY | MANUSCRIPT_EVIDENCE |
SOURCE_BASIS | DEFECT | MINIMAL_ACTION
```

## 7. Normative anchors

- IEEE, *Editorial Style Manual for Authors*:
  https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-Editorial-Style-Manual-for-Authors.pdf
- IEEE, *Reference Guide*:
  https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/IEEE-Reference-Guide.pdf
- IEEE, *Math Typesetting Guide for LaTeX Users*:
  https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/IEEE-Math-Typesetting-Guide-for-LaTeX-Users.pdf
- IEEE Author Center, *About the Peer Review Process*:
  https://journals.ieeeauthorcenter.ieee.org/submit-your-article-for-peer-review/about-the-peer-review-process/
- IEEE Author Center, *Research Reproducibility*:
  https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/research-reproducibility/

Writing sources such as Knuth's *Mathematical Writing* and Williams and
Bizup's *Style: Lessons in Clarity and Grace* provide heuristics. They do not
override the target venue or technical evidence.
