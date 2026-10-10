#!/usr/bin/env python3
"""Validate the local state manifest for a managed project NotebookLM notebook."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


SCHEMA = "project-notebook-state-guard/1.0"
REQUIRED_ROLES = ("project_context", "current_manuscript")
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and "REPLACE_WITH_" in value


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_value(repo: Path, *arguments: str) -> str | None:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def git_bytes(repo: Path, *arguments: str) -> bytes | None:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=False,
        capture_output=True,
    )
    return completed.stdout if completed.returncode == 0 else None


def compute_worktree_digest(repo: Path, excluded_paths: set[str]) -> str | None:
    """Hash current changed/untracked paths while excluding generated state files."""
    changed = git_bytes(repo, "diff", "--name-only", "-z", "HEAD", "--")
    untracked = git_bytes(repo, "ls-files", "--others", "--exclude-standard", "-z")
    if changed is None or untracked is None:
        return None
    names = {
        os.fsdecode(raw)
        for raw in (changed + untracked).split(b"\0")
        if raw
    }
    normalized_exclusions = {Path(value).as_posix() for value in excluded_paths}
    names = {name for name in names if Path(name).as_posix() not in normalized_exclusions}
    if not names:
        return "clean"

    digest = hashlib.sha256()
    for name in sorted(names):
        path = repo / name
        digest.update(name.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"SYMLINK\0")
            digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        elif path.is_file():
            digest.update(b"FILE\0")
            digest.update(file_sha256(path).encode("ascii"))
        elif path.exists():
            digest.update(b"OTHER\0")
        else:
            digest.update(b"DELETED\0")
        digest.update(b"\0")
    return digest.hexdigest()


def validate_manifest(
    document: Any,
    repo: Path,
    *,
    check_git: bool,
) -> dict[str, Any]:
    errors: list[str] = []
    stale_reasons: list[str] = []
    warnings: list[str] = []

    if not isinstance(document, dict):
        return {
            "schema": SCHEMA,
            "status": "INVALID",
            "errors": ["Manifest root must be an object."],
            "stale_reasons": [],
            "warnings": [],
        }

    if document.get("schema_version") != 1:
        errors.append("schema_version must be 1.")
    if document.get("notebook_alias") != "project":
        errors.append("notebook_alias must be 'project'.")
    for field in ("project", "notebook_title", "notebook_id"):
        value = document.get(field)
        if not nonempty(value) or is_placeholder(value):
            errors.append(f"{field} must be populated and contain no placeholder.")

    snapshot = document.get("snapshot")
    if not isinstance(snapshot, dict):
        errors.append("snapshot must be an object.")
        snapshot = {}
    snapshot_fields = ("id", "generated_at_utc")
    if check_git:
        snapshot_fields += ("git_branch", "git_head", "worktree_digest")
    for field in snapshot_fields:
        value = snapshot.get(field)
        if not nonempty(value) or is_placeholder(value):
            errors.append(f"snapshot.{field} must be populated and contain no placeholder.")

    sources = document.get("managed_sources")
    if not isinstance(sources, list) or not sources:
        errors.append("managed_sources must be a non-empty array.")
        sources = []

    roles: dict[str, dict[str, Any]] = {}
    titles: set[str] = set()
    source_ids: set[str] = set()
    checked_files = 0

    repo = repo.resolve()
    for index, source in enumerate(sources, 1):
        prefix = f"managed_sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object.")
            continue
        role = source.get("role")
        title = source.get("title")
        source_id = source.get("source_id")
        local_path = source.get("local_path")
        expected_hash = source.get("sha256")

        if not nonempty(role):
            errors.append(f"{prefix}.role is required.")
        elif role in roles:
            errors.append(f"Duplicate managed source role: {role}.")
        else:
            roles[role] = source

        if not nonempty(title):
            errors.append(f"{prefix}.title is required.")
        elif title in titles:
            errors.append(f"Duplicate managed source title: {title}.")
        else:
            titles.add(title)

        if not nonempty(source_id) or is_placeholder(source_id):
            errors.append(f"{prefix}.source_id must be populated.")
        elif source_id in source_ids:
            errors.append(f"Duplicate managed source ID: {source_id}.")
        else:
            source_ids.add(source_id)

        if not nonempty(local_path):
            errors.append(f"{prefix}.local_path is required.")
            continue
        candidate = (repo / local_path).resolve()
        try:
            candidate.relative_to(repo)
        except ValueError:
            errors.append(f"{prefix}.local_path escapes the repository: {local_path}.")
            continue
        if not candidate.is_file():
            errors.append(f"{prefix}.local_path does not exist: {local_path}.")
            continue

        if not nonempty(expected_hash) or not SHA256_RE.fullmatch(expected_hash):
            errors.append(f"{prefix}.sha256 must be a 64-character hexadecimal digest.")
            continue
        checked_files += 1
        actual_hash = file_sha256(candidate)
        if actual_hash.casefold() != expected_hash.casefold():
            stale_reasons.append(f"Hash mismatch for role {role}: {local_path}.")

    required_roles = document.get("required_roles", list(REQUIRED_ROLES))
    if (not isinstance(required_roles, list) or not required_roles
            or not all(nonempty(role) for role in required_roles)
            or len(set(required_roles)) != len(required_roles)):
        errors.append("required_roles must be a non-empty array of unique role names.")
        required_roles = list(REQUIRED_ROLES)
    for role in required_roles:
        source = roles.get(role)
        if source is None:
            errors.append(f"Missing required managed source role: {role}.")
            continue
        if source.get("required") is not True:
            errors.append(f"Role {role} must set required=true.")

    excluded_values = document.get("digest_exclusions", [])
    if not isinstance(excluded_values, list) or not all(nonempty(value) for value in excluded_values):
        errors.append("digest_exclusions must be an array of repository-relative paths.")
        excluded_values = []
    for value in excluded_values:
        candidate = (repo / value).resolve()
        if Path(value).is_absolute() or not candidate.is_relative_to(repo):
            errors.append(f"digest_exclusions contains an invalid path: {value}.")

    if check_git and not errors:
        actual_branch = git_value(repo, "branch", "--show-current")
        actual_head = git_value(repo, "rev-parse", "HEAD")
        excluded_paths = set(excluded_values)
        actual_worktree = compute_worktree_digest(repo, excluded_paths)
        if actual_branch is None or actual_head is None or actual_worktree is None:
            errors.append("Could not inspect Git state for --check-git.")
        else:
            if snapshot.get("git_branch") != actual_branch:
                stale_reasons.append(
                    f"Git branch differs: manifest={snapshot.get('git_branch')}, current={actual_branch}."
                )
            if snapshot.get("git_head") != actual_head:
                stale_reasons.append(
                    f"Git HEAD differs: manifest={snapshot.get('git_head')}, current={actual_head}."
                )
            if snapshot.get("worktree_digest") != actual_worktree:
                stale_reasons.append(
                    "Worktree digest differs: "
                    f"manifest={snapshot.get('worktree_digest')}, current={actual_worktree}."
                )

    status = "INVALID" if errors else ("STALE" if stale_reasons else "CURRENT")
    return {
        "schema": SCHEMA,
        "status": status,
        "verification_scope": "LOCAL_MANIFEST_AND_FILES",
        "remote_sources_verified": False,
        "managed_source_count": len(sources),
        "checked_file_count": checked_files,
        "snapshot_id": snapshot.get("id"),
        "errors": errors,
        "stale_reasons": stale_reasons,
        "warnings": warnings,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Validate a project-notebook state manifest and local hashes."
    )
    result.add_argument("--manifest")
    result.add_argument("--repo", required=True)
    result.add_argument("--check-git", action="store_true")
    result.add_argument(
        "--print-worktree-digest",
        action="store_true",
        help="Print the current digest without reading a manifest.",
    )
    result.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Additional repository-relative path to exclude from the digest.",
    )
    result.add_argument("--pretty", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    repo = Path(args.repo).expanduser().resolve()
    if args.print_worktree_digest:
        excluded = set(args.exclude)
        digest = compute_worktree_digest(repo, excluded)
        result = {
            "schema": SCHEMA,
            "status": "CURRENT" if digest is not None else "INVALID",
            "worktree_digest": digest,
            "excluded_paths": sorted(excluded),
            "errors": [] if digest is not None else ["Could not inspect Git worktree."],
            "stale_reasons": [],
            "warnings": [],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0 if digest is not None else 2
    if not args.manifest:
        parser().error("--manifest is required unless --print-worktree-digest is used.")
    try:
        manifest_path = Path(args.manifest).expanduser().resolve()
        document = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        result = validate_manifest(document, repo, check_git=args.check_git)
    except (OSError, json.JSONDecodeError) as exc:
        result = {
            "schema": SCHEMA,
            "status": "INVALID",
            "errors": [f"{type(exc).__name__}: {exc}"],
            "stale_reasons": [],
            "warnings": [],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return {"CURRENT": 0, "STALE": 1, "INVALID": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
