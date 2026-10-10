# Contributing

Fork the repository, make a focused change, and open a pull request describing
the problem, resulting behavior, and validation. Contributions are under the
repository's MIT license. No contributor agreement is required.

Keep the workflow general: project facts, notebook bindings, scientific results,
and author preferences belong with the paper. Load detailed guidance only when
needed. Preserve the distinction between local evidence, notebook inference,
author decisions, and mechanical checks. Never claim an improved acceptance rate
or scientific accuracy from package validation alone.

Use Python 3.10+ and run the offline checks from the repository root:

```sh
python -m unittest discover -s paper-revision/tests -v
python -m unittest discover -s tests -v
python scripts/check_package.py
```

These checks need no Google account, network, API keys, or third-party packages.
CI runs them on Windows, macOS, and Linux. Use meaningful behavior tests for tools
that change evidence, approval, installation, or source ownership. Instructions
also need realistic review; passing a schema validator does not prove good prose.

Use synthetic examples. Never submit personal configs, real source/notebook IDs,
cookies, auth profiles, receipts containing unpublished work, manuscript excerpts
without publication permission, or copied books/manuals. Run a local privacy check
before publishing an example. Do not use private source fixtures to reproduce a bug.

For integration changes, state the tested `notebooklm-py` version and backend.
Live tests are opt-in, use a contributor-owned disposable notebook and synthetic
text, and must not appear in ordinary CI. Do not alter or delete a user's notebooks
as part of a test. Review an upstream version bump before changing the pin.

Maintain links and the installable package's license. If you copy third-party code
or text, keep its required notices and document provenance. Add an external
dependency only for a concrete capability; the local workflow should stay usable
without NotebookLM.
