#!/usr/bin/env python3
"""Install the complete Paper Revision skill without touching account configuration."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "paper-revision"
HOST_DIRS = {"codex": (".agents", "skills"), "claude": (".claude", "skills"),
             "gemini": (".gemini", "skills")}


def install(base: Path, *, update: bool = False, dry_run: bool = False) -> dict:
    base = base.expanduser().resolve()
    source = ROOT / NAME
    destination = base / NAME
    if not (source / "SKILL.md").is_file() or not (ROOT / "LICENSE").is_file():
        raise ValueError("The repository is incomplete: skill and license are required.")
    if destination.is_symlink():
        raise ValueError("Refusing to replace a symlink installation.")
    if destination.exists() and not destination.is_dir():
        raise ValueError("The destination is a file, not a skill directory.")
    if source.resolve() == destination.resolve() or source.resolve() in destination.resolve().parents:
        raise ValueError("Choose a destination outside the source skill.")
    if destination.exists() and not update:
        raise ValueError("Skill already exists; use --update to replace it with a ZIP backup.")
    if destination.exists() and not (destination / "SKILL.md").is_file():
        raise ValueError("Existing directory is not a skill; refusing to replace it.")
    result = {"skill": NAME, "destination": str(destination),
              "status": "DRY_RUN" if dry_run else "INSTALLED", "backup": None}
    if dry_run:
        return result
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".paper-revision-install-", dir=base) as temporary:
        work = Path(temporary).resolve()
        work.relative_to(base)  # Temporary cleanup is confined to this generated directory.
        staged = work / NAME
        shutil.copytree(source, staged, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc", "*.pyo"))
        shutil.copy2(ROOT / "LICENSE", staged / "LICENSE")
        previous = work / "previous"
        if destination.exists():
            backups = base / ".paper-revision-backups"
            backups.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = backups / f"{NAME}-{stamp}-{uuid.uuid4().hex[:8]}.zip"
            with zipfile.ZipFile(backup, "x", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(destination.rglob("*")):
                    if path.is_file():
                        archive.write(path, Path(NAME) / path.relative_to(destination))
            result["backup"] = str(backup)
            os.replace(destination, previous)
        try:
            os.replace(staged, destination)
        except OSError:
            if previous.exists():
                os.replace(previous, destination)
            raise
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    location = parser.add_mutually_exclusive_group()
    location.add_argument("--agent", choices=HOST_DIRS, default=None)
    location.add_argument("--dest", type=Path, help="Parent skills directory; paper-revision is created inside it.")
    parser.add_argument("--update", action="store_true", help="Replace an existing skill after a ZIP backup.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    base = args.dest if args.dest is not None else Path.home().joinpath(*HOST_DIRS[args.agent or "codex"])
    try:
        result = install(base, update=args.update, dry_run=args.dry_run)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
