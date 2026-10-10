#!/usr/bin/env python3
"""Check the public package's local links, structure, and accidental credential files."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "paper-revision"


def check(root: Path = ROOT) -> dict:
    errors = []
    skill = root / "paper-revision"
    entry = skill / "SKILL.md"
    text = entry.read_text(encoding="utf-8")
    if not text.startswith("---\nname: paper-revision\n") or "\ndescription: " not in text:
        errors.append("Skill frontmatter is missing its expected name or description.")
    for required in ("LICENSE", "README.md", "install.py", "requirements-notebooklm.txt"):
        if not (root / required).is_file():
            errors.append(f"Missing repository file: {required}")
    files = [path for path in root.rglob("*") if path.is_file()
             and ".git" not in path.parts and "__pycache__" not in path.parts]
    forbidden = {"storage_state.json", "master_token.json", "notebooklm_config.json", "notebooklm-config.json"}
    for path in files:
        if path.name in forbidden or path.name == ".env" or ".notebooklm" in path.parts:
            errors.append(f"Private runtime artifact in public package: {path.relative_to(root)}")
        if path.suffix != ".md":
            continue
        contents = path.read_text(encoding="utf-8")
        # Only literal Markdown links, not shell examples or variable paths.
        for target in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", contents):
            target = target.strip().strip("<>").split("#", 1)[0]
            if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            resolved = (path.parent / unquote(target)).resolve()
            if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                errors.append(f"Broken local link in {path.relative_to(root)}: {target}")
    config = json.loads((skill / "references/notebooklm-config.example.json").read_text(encoding="utf-8"))
    if any(entry.get("id") for entry in config.get("notebooks", {}).values()):
        errors.append("Notebook example must not bind any real notebook.")
    return {"status": "PASS" if not errors else "FAIL", "files_checked": len(files), "errors": errors}


if __name__ == "__main__":
    result = check()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
