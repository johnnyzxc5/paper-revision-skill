# Paper Revision

[Español](README.es.md) · [MIT license](LICENSE) · [Contributing](CONTRIBUTING.md)

An agent skill for writing and revising scientific papers without losing the
connection between claims and evidence. It supports drafting, mathematical
exposition, reviewer comments, response letters, citation checks, and verification
of applied changes. It includes the instructions, references, Python tools, and
offline regression tests in one repository.

Use it with your own manuscripts, data, reviewers, venues, and source libraries.
The workflow applies across scientific fields; its document tooling is strongest
for LaTeX. It does not assume a particular paper, institution, writing library,
notebook account, or reviewer roster.

## Ask your agent to install it

Copy this request into an agent with filesystem and shell access:

```text
Install Paper Revision from https://github.com/johnnyzxc5/paper-revision-skill.
Read its README and install the paper-revision skill in this agent's skill
directory. Use the repository's installer or copy the complete paper-revision
folder, including scripts and references. Preserve any existing installation.
Use the local workflow first; set up NotebookLM only if I ask for it.
```

Manual installation (Python 3.10+ and Git):

```sh
git clone https://github.com/johnnyzxc5/paper-revision-skill.git
cd paper-revision-skill
python install.py --agent codex
```

The installer copies the skill and its MIT license. It makes no network requests,
installs no packages, and creates no notebook credentials. It refuses an existing
installation by default. Use `--update` to replace it with a ZIP backup retained
under the destination's `.paper-revision-backups/` directory.

| Host | Command / destination |
| --- | --- |
| Codex or shared Agent Skills directory | `python install.py --agent codex` → `~/.agents/skills/paper-revision` |
| Claude Code | `python install.py --agent claude` → `~/.claude/skills/paper-revision` |
| Gemini-compatible skill directory | `python install.py --agent gemini` → `~/.gemini/skills/paper-revision` |
| Another host or project-local installation | `python install.py --dest /path/to/skills` |
| Older/custom Codex directory | `python install.py --dest ~/.codex/skills` |

Restart or refresh the host's skill discovery if needed. Directory and invocation
support depend on the host; the core requirements are reading `SKILL.md` and
running Python helpers. No particular host/model version is required.

## Start with your paper

```text
Use $paper-revision to audit manuscript.tex and references.bib. My goal is to
make the contribution and evidence boundaries clear. Do not edit files yet;
show material findings with their anchors. There are no reviewer comments.
```

```text
Use $paper-revision to revise the Results subsection in manuscript.tex against
reviewer-comments.pdf. Preserve the reported values and inspect the supporting
tables/code. Show the correction strategy and exact proposed text for approval.
```

```text
Use $paper-revision to draft the Methods section from my supplied protocol and
analysis code. Mark missing details instead of inventing them. Target the venue
in my project notes and use my established notation.
```

The default workflow reviews evidence, presents a substantive correction strategy
for author choice, and then presents the exact draft for separate approval.
It checks the actual applied diff and compilation afterward. The author's explicit
instructions and the host's instruction hierarchy control authorization. An audit
does not edit the manuscript. With no reviewers, there is no invented reviewer ledger.

## Do I need NotebookLM or notebooklm-py?

**No, for local writing and revision.** Local tools use only Python's standard
library. Your paper's LaTeX/build dependencies remain project-specific.

**Yes, only for the included NotebookLM integration.** Install the external
[notebooklm-py package](https://github.com/teng-lin/notebooklm-py) in an isolated
environment and log in with your own Google account. You do not need to clone its
repository or install a companion skill/MCP server. This integration authenticates
through the client's profile; it does not use a NotebookLM API key in this repo.

Read [the setup guide](paper-revision/references/notebooklm-setup.md) for complete
Windows/macOS/Linux commands, profile setup, empty notebook aliases, and a test query.
The optional dependency is pinned in [requirements-notebooklm.txt](requirements-notebooklm.txt).
The client is a community project using undocumented endpoints, so service
compatibility can change independently of this skill.

The package contains query and source-management wrappers. Configure your own
`project`, `theory` (domain evidence), and `writing` roles as needed. The bundled
writing registry is an example you customize to your own source titles; no manuals
or copyrighted PDFs are included. Receipts check what was queried and returned,
but a notebook verdict or a passing guard does not prove scientific correctness.

## Included tools

All scripts live in `paper-revision/scripts/`; use `python <script> --help` for
their exact arguments. Examples are synthetic/templates, never real approvals or
receipts to reuse in your paper.

| Tool | Purpose |
| --- | --- |
| `revision_guard.py` | Validate reviewer ledgers, counts, anchors, scoped literal absence checks, and generate a Markdown view |
| `route_guard.py` | Validate correction routes and their evidence/decision records |
| `manuscript_approval_guard.py` | Bind strict author approval to the exact candidate hash |
| `notebooklm_receipt_guard.py` | Validate prompt/receipt consistency for route and candidate audits |
| `writing_review_guard.py` | Check exact-block coverage, source fidelity, and local semantic review records |
| `writing_source_router.py` | Resolve a chosen source registry against a writing-notebook inventory |
| `project_notebook_guard.py` | Check configurable project-context source roles, local hashes, and optional Git snapshot state |
| `notebooklm_tool.py` | Query notebooks with aliases, bounded retries, batch concurrency, and saved JSON receipts |
| `notebooklm_sources.py` | Manage owned rubrics and temporary review sources with fidelity checks |
| `doi_bibtex.py` | Retrieve DOI-linked BibTeX with explicit caching; citation support still needs inspection |
| `context_snapshot.py` | Cache local file hashes for resuming work |
| `latex_log_summary.py` | Summarize actual LaTeX logs |

## Privacy and reuse

Keep personal notebook config, login profiles/cookies/tokens, source IDs, manuscript
uploads, prompts, and receipts in a private project workspace. Add that workspace
to your manuscript repository's ignore rules. Do not paste credentials into chat.
An installation or config file is not authorization to upload unpublished work.

The public package has no personal notebook bindings, manuscript excerpts from
its originating project, personal paths, or inherited Git history.

The MIT license permits use, modification, redistribution, and commercial use
with the license/copyright notice retained. There is no requirement to credit
this skill in your paper. External packages and books retain their own licenses.
Forks, issues, and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md)
for offline tests and safe example data.
