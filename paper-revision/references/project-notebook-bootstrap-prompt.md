# Optional project-notebook bootstrap request

Adapt the bracketed fields before sending this to an agent:

```text
Use $paper-revision to set up a project-context NotebookLM notebook for
[project name] using my private config at [config path]. I authorize uploading
[exact source files] to [notebook ID]. Manage only sources recorded as owned by
this project. Do not edit the manuscript or reset conversation history.

Read references/project-notebook-protocol.md. Inspect the current manuscript,
its evidence, and any actual reviewer/dependency records. Verify the manuscript
export, generate a bounded context pack, and populate the state manifest with
current hashes. Include only source roles needed for this project. Report missing
inputs honestly and never create fictitious reviewer comments.

Use my existing notebook if selected; ask for the notebook choice if missing.
Preserve unrelated sources. Verify the processed sources against local files and
record source IDs and operation receipts. Validate the local state and summarize
what is current, stale, or blocked. Do not treat local guard success as a live
NotebookLM currency check.
```
