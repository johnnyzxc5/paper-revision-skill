# Query contracts

Read this reference when preparing `batch` input or consuming wrapper output.

## Config

```json
{
  "schema_version": 1,
  "python_executable": "C:/path/to/python.exe",
  "profile": "default",
  "backend": "web",
  "max_prompt_chars": 3500,
  "request_timeout_seconds": 90,
  "max_attempts": 2,
  "max_concurrency": 2,
  "active_history_poll_default": true,
  "history_poll_interval_seconds": 2.5,
  "progress_heartbeat_seconds": 10.0,
  "diagnostics_mode_default": "summary",
  "fresh_default": false,
  "notebooks": {
    "project": {"id": "project-notebook-uuid", "title": "Active project context"},
    "theory": {"id": "notebook-uuid", "title": "Theory notebook"},
    "writing": {"id": "notebook-uuid", "title": "Academic writing"}
  }
}
```

`python_executable` must point to the environment that contains
`notebooklm-py`. Titles are documentation; the wrapper resolves aliases by
their configured IDs so similarly named notebooks cannot be selected silently.
Project aliases with an empty ID are intentionally unbound and fail locally
until the user or bootstrap workflow records the UUID returned by `list`.

For a direct route or candidate query, pass its stable logical identifier with
`ask --query-id`. The fallback ID `single` is suitable only for ad-hoc
diagnostics and is not auditable evidence for a route decision. Batch queries
already take their IDs from the input manifest.

Preserve the exact prompt file and the complete wrapper JSON for auditable
queries. The paper-revision receipt guard compares the normalized
prompt hash with `result.request.question_sha256`, verifies notebook/source
scope, and binds the result to the route manifest. Copying the answer alone or
manually typing a query ID is insufficient.

For normal agent execution, save the full receipt without sending it through
the conversation:

```powershell
& $python $tool --config $config batch -f queries.json `
  --output-file receipts/route-r1.json --compact-output
```

The receipt is written atomically. Existing files are refused unless
`--overwrite-output` is supplied deliberately. An overwrite archives the prior
bytes as a unique `.superseded-*` sibling and reports that archive in the compact
card. This recovery feature is for non-audit work: route and candidate evidence
must always use a new query ID and output path, and the academic receipt guard
rejects a path with a superseded predecessor. `--compact-output` requires an
output file and returns a bounded decision card; the complete answer and full
references remain in the saved receipt. Do not use `--pretty` for machine
consumption.

## Batch input

The preferred root is an object with a `queries` array. A bare array remains
accepted for backward compatibility.

```json
{
  "schema_version": 1,
  "queries": [
    {
      "id": "C1-theory-evidence",
      "notebook": "theory",
      "question_file": "prompts/C1-theory.txt",
      "source_ids": ["source-uuid"],
      "fresh": false,
      "active_history_poll": true,
      "history_poll_interval_seconds": 2.5,
      "heartbeat_seconds": 10.0,
      "diagnostics_mode": "summary",
      "timeout_seconds": 90,
      "attempts": 2
    },
    {
      "id": "C1-editorial-audit",
      "notebook": "writing",
      "question": "Self-contained atomic question...",
      "fresh": false
    }
  ]
}
```

Rules:

- `id` must be unique and stable enough to cite in the revision ledger.
- `notebook` is a config alias or an explicit notebook ID.
- Supply exactly one of `question` and `question_file`.
- Relative `question_file` paths resolve from the batch file's directory.
- `source_ids` is optional. Use it when the requested evidence is confined to
  known documents.
- `fresh` and `conversation_id` are mutually exclusive.
- `active_history_poll` defaults to the config setting. When enabled, the
  wrapper probes history while the direct call is running and accepts only an
  exact unique-marker match.
- `history_poll_interval_seconds` controls bounded polling; do not reduce it
  aggressively against the real service.
- `heartbeat_seconds` controls liveness messages on `stderr`; set it to `0` to
  disable them. `stdout` remains a single JSON result.
- `diagnostics_mode` is `off`, `summary`, or `full`. Use `summary` for ordinary
  work. Use `full` only for a saved transport postmortem.

## Output

```json
{
  "schema": "notebooklm-agent-wrapper/2.5.2",
  "command": "batch",
  "status": "success",
  "counts": {"total": 2, "succeeded": 2, "failed": 0},
  "results": [
    {
      "query_id": "C1-theory-evidence",
      "status": "success",
      "notebook_id": "notebook-uuid",
      "attempts": 1,
      "elapsed_ms": 12345,
      "retrieval_method": "direct_cli",
      "request": {
        "question_sha256": "...",
        "prompt_chars": 1840,
        "submitted_chars": 1905,
        "client_request_id": "...",
        "source_ids": ["source-uuid"],
        "fresh": false,
        "conversation_id": null,
        "active_history_poll": true
      },
      "answer": "...",
      "references": [],
      "diagnostics": {
        "mode": "summary",
        "history_polls_count": 4,
        "time_to_exact_history_match_ms": 12345
      }
    }
  ]
}
```

With `--compact-output`, stdout instead contains the receipt path and SHA-256,
plus one compact result per query: status, request hash and source scope,
answer hash/size, parsed verdict/evidence fields, intermediate failures, and a
diagnostic summary. Treat this card as navigation; the saved receipt remains
the evidence validated by the academic revision guards.

Top-level states:

- `success`: every query succeeded;
- `partial`: at least one succeeded and at least one failed;
- `error`: none succeeded, or the input/tool failed before execution.

A successful individual result in a partial batch can be validated; do not
label the overall consultation complete until all required roles are covered.
Coordinated same-notebook queries must use one batch to share its lock.

The process exits `0` only when all requested operations succeed, `1` for an
upstream/partial failure, `2` for invalid input or an internal wrapper error,
and `130` when interrupted.

## Structured prompt example

Use labeled fields in this order:

```text
TASK_ID: C1-theory-evidence
ROLE: Source-grounded domain-evidence auditor.
DECISION: Determine whether the proposed sentence is supportable.
KNOWN_CONTEXT: [only facts required to interpret the fragment]
REVIEWER_REQUIREMENT: [verbatim or faithful paraphrase]
CURRENT_TEXT: [exact LaTeX fragment]
CHECKS:
1. ...
2. ...
OUTPUT: Return VERDICT, EVIDENCE, DEFECTS, and MINIMAL_CORRECTION.
Do not repeat the prompt or candidate. Use at most three evidence items and
keep MINIMAL_CORRECTION below 100 words.
If the sources do not establish a claim, write INSUFFICIENT_EVIDENCE.
```

Avoid conversational setup, project history, praise, and requests for a
numerical score. They consume the prompt budget without improving the evidence.
