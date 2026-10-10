# Host runtime and tools

This is a portable `SKILL.md` package for agents that can read files and run
Python. Codex UI metadata is optional; other hosts can use the same instructions.
Resolve scripts and references relative to the installed `paper-revision` folder.
The writing and review workflow is useful across scientific domains; LaTeX
candidate presentation and compilation procedures apply only to LaTeX projects.
For other formats, use their native source/diff/build tools and preserve the same
evidence and author-decision boundaries.

Local scripts use Python 3.10+ and its standard library. `doi_bibtex.py` uses
network access only for explicit DOI retrieval; guards and offline tests do not
need network access. Manuscript compilation uses the project's existing tools.
For a standalone LaTeX document, a host's built-in compiler may be suitable;
multi-file projects use their own build procedure.

## Optional NotebookLM

The wrapper and source helper are included in `scripts/`. No companion skill,
MCP server, or clone of the upstream repository is required. Install the community
`notebooklm-py` package in a Python environment and authenticate with your own
Google account. See [NotebookLM setup](notebooklm-setup.md).

Pass the project's explicit `--config` path. Its `python_executable` must point to
the environment containing `notebooklm-py`; when omitted, the wrapper uses its own
Python interpreter. Configure only the aliases actually needed for this paper.
Do not assume that an existing notebook belongs to the current project.

Keep configuration, credentials, source ownership state, prompts, and receipts
outside the installed skill. A reinstall must not reset project state. Hosts
sharing a notebook must also share its source ownership state and serialize
mutations using the helper's lock. Keep one managed rubric per writing notebook,
with project-qualified keys for temporary review sources. Content hashes allow
the same rubric bytes to be verified even when host installation paths differ.

The community client uses undocumented endpoints; record its version and treat
authentication, transport, or response-shape failures as actual failures.
Never silently upgrade packages, switch profiles/backends, reset conversation
history, or rewrite credentials to compensate for an error.
