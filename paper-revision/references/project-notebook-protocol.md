# Optional project-context notebook

Use this only when the author wants a NotebookLM notebook recording the current
paper's state. It is separate from domain sources and writing guidance. Local
files remain authoritative for what the manuscript currently contains.
No project notebook is needed for ordinary local writing or review.

## Choose sources for this paper

Use author-selected titles and project-qualified source names; there are no fixed
title requirements. Start with the current manuscript and a context pack derived
from inspected evidence. Add actual reviewer comments, a reviewer ledger, a
dependency ledger, notation registry, or response letter only when they exist and
matter to the requested task. Never fabricate reviewer material for a new paper.

Uploading a manuscript or comments requires authorization for NotebookLM.
When using a compiled PDF as the current manuscript, first verify that it was
successfully built from the current source. A stale PDF must not become the
notebook's current truth. For other formats, use the corresponding verified export.

## State manifest

Copy `project-notebook-state.example.json` into the private project workspace.
Populate notebook/source IDs, repository-relative file paths, hashes, snapshot
time, and Git state when available. Set `required_roles` to the roles required
for this task. The default core roles are `project_context` and
`current_manuscript`; add `reviewer_ledger` and `ripple_effects` only for a
reviewer/dependency workflow that actually needs them. Mark those sources
`required=true`. Additional roles may be optional, but their files and hashes
are still checked if included in the manifest.

```sh
python /path/to/paper-revision/scripts/project_notebook_guard.py --manifest .paper-revision/project-state.json --repo . --pretty
```

Git checking is optional. For a Git project, record explicit `digest_exclusions`
for the generated manifest/context files, then compute a digest with matching
`--exclude` arguments and validate using `--check-git`. Exclusions must not hide
manuscript, data, code, or other scientific inputs.

```sh
python /path/to/paper-revision/scripts/project_notebook_guard.py --repo . --print-worktree-digest --exclude .paper-revision/project-state.json --exclude .paper-revision/project-context.md
python /path/to/paper-revision/scripts/project_notebook_guard.py --manifest .paper-revision/project-state.json --repo . --check-git --pretty
```

The guard checks local consistency. It does not inspect NotebookLM, prove source
currency, authenticate a receipt, or establish scientific truth. Before relying
on notebook context, list its live sources, verify the intended source IDs/titles,
and check that processed content matches the current local snapshot. If those
checks are unavailable, label currency unverified; do not claim a current
whole-paper consultation.

## Synchronization and query boundaries

Use [project-context-pack.template.md](project-context-pack.template.md) as a
starting point, removing irrelevant headings. Its contents come from the author's
paper, never from an example project. Keep accepted decisions distinct from
unselected routes, drafted text, deferred work, and historical claims.

The bundled `notebooklm_sources.py` manages rubrics and temporary exact-block
review sources. It is not a general manuscript/ledger synchronizer. For project
sources, use the public upstream source CLI within the author's explicit source
management scope, preserve operation receipts, and verify new sources before
retiring sources owned by this project. Never delete by title alone or reset
conversation history during cleanup. A failed remote write needs inspection;
do not retry blindly and create duplicate sources.

Query `project` only for an unresolved accepted decision, reviewer interpretation,
or dependency after local inspection. Supply the snapshot ID and exact relevant
fragment, restrict to current sources, and require `SNAPSHOT_MATCH` plus any
missing local evidence. A mismatch invalidates use of that answer as current state.
Do not use project summaries to decide domain truth or venue rules.

After an accepted material change, update local state and only the managed remote
sources whose content actually changed. Reuse unchanged verified source bindings.
Record any remaining sync limitation separately from manuscript readiness.
