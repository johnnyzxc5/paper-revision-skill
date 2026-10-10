# Semantic context and change containment

## Context envelope and change containment

Before diagnosing a target block, inspect a semantic context envelope rather
than an arbitrary line window:

- the complete target subsection or logical block;
- the complete preceding and following paragraph/block that controls its
  transition and information flow;
- every earlier definition, assumption, acronym, and symbol used by the target;
- all materially dependent later occurrences identified by search and the
  ripple ledger;
- the section-purpose and abstraction contract in the project profile.

Record what is inherited from earlier text, what genuinely becomes new here,
and what must be deferred to the following block. A fixed `±15`-line window may
be used for navigation, but it is never proof that context was checked.

Before proposing routes, list `protected_anchors`: equations, definitions,
lists, claims, captions, or paragraphs outside the requested correction that
must remain unchanged. Do not shorten, restyle, rename, or delete them as a
side effect. If evidence shows that a protected neighbor also needs revision,
surface it as a separate route/scope request and wait for the user; do not hide
it inside the current candidate. Necessary ripple edits must be named and
approved, not smuggled in as cleanup.

Check the global notation and acronym registries before introducing any symbol
or abbreviation. Use [references/manuscript-registry.example.json](manuscript-registry.example.json)
as a compact schema when the project has no registry. Populate it from current
text; unresolved entries remain author-side findings, not invented definitions. Check the candidate against the section's abstraction
contract: preserve general mechanisms in general-method sections and defer
named platforms, fault instances, algorithms, solvers, datasets, and
hyperparameters to the layer where they belong. This is a semantic check, not a
blind banned-word replacement.

If the project records withdrawn/limited claims, inspect entries governing this
block using [claim-history.md](claim-history.md). Record completed neighboring
blocks and deliberately deferred work separately. Context inspection does not
authorize rewriting either; preserve the author's staged plan and identify
necessary future propagation explicitly.
