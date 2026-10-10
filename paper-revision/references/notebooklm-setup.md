# Optional NotebookLM setup

The base skill needs no NotebookLM account or Python package dependencies.
This integration uses [teng-lin/notebooklm-py](https://github.com/teng-lin/notebooklm-py),
an independent community client, through its public CLI. It uses Google account
authentication; there is no NotebookLM API key to paste into this skill.
No clone of that repository or separate NotebookLM skill is needed.

The wrapper targets the 0.8 CLI family. Start with the version in the repository's
`requirements-notebooklm.txt` (`0.8.2`) and test upgrades deliberately. Offline
tests verify local behavior, not continuing compatibility with Google's service.
Upstream [installation documentation](https://github.com/teng-lin/notebooklm-py/blob/main/docs/installation.md)
and [authentication documentation](https://github.com/teng-lin/notebooklm-py/blob/main/docs/auth-cookie-lifecycle.md)
are authoritative for login options.

## 1. Install in an isolated environment

From a clone of this repository:

```sh
python -m venv .venv-notebooklm
```

On Windows PowerShell:

```powershell
.\.venv-notebooklm\Scripts\python.exe -m pip install -r requirements-notebooklm.txt
.\.venv-notebooklm\Scripts\python.exe -m notebooklm --profile paper-revision login
.\.venv-notebooklm\Scripts\python.exe -m notebooklm --profile paper-revision auth check --test
```

On macOS/Linux:

```sh
.venv-notebooklm/bin/python -m pip install -r requirements-notebooklm.txt
.venv-notebooklm/bin/python -m notebooklm --profile paper-revision login
.venv-notebooklm/bin/python -m notebooklm --profile paper-revision auth check --test
```

Login is interactive; the user signs in locally. Credentials belong in the
client's profile storage, never in this repo or a shared manuscript bundle.
The default here is the Web backend. Android is optional, requires upstream's
`[android]` extra and its documented authentication, and is never switched on
automatically by this skill.

## 2. Bind your own notebooks

Copy `notebooklm-config.example.json` to a private project directory, such as
`.paper-revision/notebooklm-config.json`. If running the wrapper with a different
interpreter, add a `python_executable` field containing the absolute path of the
environment's Python. Alternatively, invoke the wrapper with the environment's
Python and leave that field omitted. List notebooks with:

```sh
python /path/to/paper-revision/scripts/notebooklm_tool.py --config .paper-revision/notebooklm-config.json --pretty list
```

Put each selected full notebook ID into the corresponding alias's `id` field.
Leave unused aliases empty. An empty or missing `project`, `theory`, or `writing`
binding fails locally instead of accidentally using another notebook. `theory`
means your paper's technical/domain sources, including nonmathematical domains.
Each role can be omitted when unnecessary. Do not combine writing manuals with
domain evidence in an answer that purports to establish scientific validity.

```sh
python /path/to/paper-revision/scripts/notebooklm_tool.py --config .paper-revision/notebooklm-config.json doctor
python /path/to/paper-revision/scripts/notebooklm_tool.py --config .paper-revision/notebooklm-config.json --pretty sources -n writing
```

Add `.paper-revision/`, login storage, and `.venv-notebooklm/` to your manuscript
repository's `.gitignore` if those directories are private. This repository's
ignore file cannot protect files committed in another project.

## 3. Query and retain the evidence

```sh
python /path/to/paper-revision/scripts/notebooklm_tool.py --config .paper-revision/notebooklm-config.json ask -n theory --query-id C1-theory-route-r1 --question-file .paper-revision/prompt.txt --output-file .paper-revision/receipts/C1-theory-route-r1.json --compact-output
```

Read [query contracts](query-contracts.md) for batches and exact-source scopes,
and [NotebookLM workflow](notebooklm-workflow.md) for audit-specific rules.
`fresh=false` is the default. `fresh=true` deletes remote conversation history;
it is not a harmless isolation option. The wrapper's prompt-size budget is a
configurable local limit, not a universal Google limit.

For writing review, copy and customize `writing-source-routing.json` using your
actual source titles, roles, and profiles. It is an illustrative library, not a
list of books you must acquire. No manuals or copyrighted PDFs are distributed.
The bundled rubric organizes checks; it cannot prove a scientific or venue rule.
Pass your registry to `writing_source_router.py --registry <path>`.
For source uploads, fidelity verification, and cleanup, read
[source management](source-management.md). Only explicitly owned/adopted sources
can be removed; user-managed manuals and unrelated notebooks remain outside scope.

## Failure and privacy

Missing required access is `BLOCKED`; optional consultation can be omitted with
an honest local assessment. Do not invent a response or drop required source
scopes on retry. Prompts, receipts, notebooks, and temporary uploads may contain
unpublished work. Use the external service only within the author's authorized
scope; do not ask the user to paste cookies, tokens, or passwords into agent chat.
