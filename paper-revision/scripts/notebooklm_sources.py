#!/usr/bin/env python3
"""Manage versioned review sources through the installed public NotebookLM CLI.

This module does not change ask, retries, conversation history or answer recovery.
All remote operations have saved receipts; no blind retry follows a failed write.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import notebooklm_tool as transport


SCHEMA = "notebooklm-managed-sources/1"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize(text: str) -> str:
    # No equation, whitespace-in-line, Markdown or Unicode rewriting.
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def literal_upload(text: str) -> str:
    """Protect copied Markdown/LaTeX from NotebookLM's Markdown conversion.

    A language label becomes extra text in the Web fulltext rendition. Use
    no label, and a fence longer than every backtick run inside the payload.
    The retrieved content must still equal the original local text; the
    fence is a transport envelope, never a license to normalize lost content.
    """
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(8, longest + 1)
    return f"{fence}\n{text}\n{fence}"


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise transport.InputError(f"Expected a JSON object: {path}")
    return value


def save_state(path: Path, state: dict) -> None:
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def state_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise transport.InputError("Source state is in use; inspect an abandoned lock before removing it.") from exc
    try:
        os.close(descriptor)
        yield
    finally:
        lock.unlink(missing_ok=True)


def load_state(path: Path, notebook: str) -> dict:
    state = read_json(path) if path.exists() else {
        "schema": SCHEMA, "notebook_id": notebook, "owner_id": uuid.uuid4().hex,
        "sources": {}, "pending": [], "retired": [],
    }
    if (state.get("schema") != SCHEMA or state.get("notebook_id") != notebook
            or not re.fullmatch(r"[a-f0-9]{32}", state.get("owner_id", ""))
            or not isinstance(state.get("sources"), dict)):
        raise transport.InputError("Invalid source state or notebook mismatch.")
    return state


class CLI:
    def __init__(self, prefix: list[str], receipts: Path):
        self.prefix = [prefix[0], "-X", "utf8", *prefix[1:]]
        self.receipts = receipts

    async def call(self, label: str, argv: list[str], text: str | None = None) -> tuple[dict, str]:
        self.receipts.mkdir(parents=True, exist_ok=True)
        output = await transport.run_process(self.prefix + ["source", *argv], stdin_text=text,
                                             outer_timeout_seconds=60)
        try:
            payload = json.loads(output.stdout)
        except json.JSONDecodeError:
            payload = {"error": "Non-JSON CLI response", "stdout": output.stdout}
        receipt = {"schema": "notebooklm-source-operation/1", "operation": label,
                   "exit_code": output.returncode, "result": payload,
                   "stderr": output.stderr, "elapsed_ms": output.elapsed_ms}
        target = self.receipts / f"{label}-{uuid.uuid4().hex}.json"
        transport.write_receipt(str(target), receipt, False)
        if output.returncode or not isinstance(payload, dict) or payload.get("error"):
            raise transport.InputError(f"Source operation failed; no automatic retry. Receipt: {target}")
        return payload, str(target.resolve())


async def fetch_verified(cli: CLI, notebook: str, source_id: str, title: str,
                         expected: str | None = None) -> tuple[dict, str]:
    details, _ = await cli.call("get", ["get", source_id, "-n", notebook, "--json"])
    details = details.get("source", details)
    if details.get("id") != source_id or details.get("title") != title or details.get("status") != "ready":
        raise transport.InputError("Source ID/title/status mismatch; source is not verified READY.")
    fulltext, receipt = await cli.call("fulltext", ["fulltext", source_id, "-n", notebook, "--json"])
    if fulltext.get("source_id") != source_id or fulltext.get("title") != title:
        raise transport.InputError("Retrieved content belongs to a different source.")
    content = fulltext.get("content")
    if not isinstance(content, str) or not content.strip():
        raise transport.InputError("Source has no retrievable content.")
    if expected is not None and normalize(content) != normalize(expected):
        raise transport.InputError("Processed source differs from the local text; do not audit a lossy upload.")
    return fulltext, receipt


def ownership(entry: dict, state: dict) -> bool:
    if entry.get("managed_by") != state["owner_id"]:
        return False
    if entry.get("adopted_rubric"):
        return entry.get("role") == "RUBRIC" and bool(re.fullmatch(
            r"Technical Scientific Paper Revision Rubric v[0-9.]+", entry.get("title", "")))
    return entry.get("title", "").startswith(f"APR__{state['owner_id']}__")


async def retire(cli: CLI, state: dict, entry: dict) -> None:
    if not ownership(entry, state):
        raise transport.InputError("Refusing to delete a source not owned by this state.")
    verification_path = Path(entry["verification_file"])
    if sha(verification_path.read_bytes()) != entry.get("verification_sha256"):
        raise transport.InputError("The saved source verification receipt changed.")
    snapshot = read_json(verification_path)["result"]
    await fetch_verified(cli, state["notebook_id"], entry["source_id"], entry["title"], snapshot["content"])
    deleted, receipt = await cli.call("delete", ["delete", entry["source_id"], "-n", state["notebook_id"],
                                          "--yes", "--json"])
    if deleted.get("success") is not True or deleted.get("source_id") != entry["source_id"] or deleted.get("notebook_id") != state["notebook_id"]:
        raise transport.InputError("Deletion is not confirmed for the exact managed source/notebook.")
    entry = dict(entry, deletion_receipt=receipt)
    state["retired"].append(entry)


async def sync(cli: CLI, state_path: Path, state: dict, key: str, file: Path,
               role: str, candidate: Path | None = None, adopt_rubric_id: str | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", key):
        raise transport.InputError("Invalid source key.")
    if any(item.get("key") == key for item in state.get("pending", [])):
        raise transport.InputError("This key has a pending operation; recover its recorded source before another write.")
    raw = file.read_bytes()
    text = raw.decode("utf-8-sig")
    if not text.strip():
        raise transport.InputError("Cannot upload an empty source.")
    if role == "TEMPORARY" and candidate is None:
        raise transport.InputError("Temporary review sources require --candidate for approval binding.")
    candidate_hash = sha(candidate.read_bytes()) if candidate else None
    if role == "TEMPORARY":
        declared = re.findall(r"(?m)^CANDIDATE_SHA256: ([0-9a-f]{64})$", normalize(text))
        blocks = re.findall(r"(?ms)^REVIEW_TEXT_BEGIN\n(.*?)^REVIEW_TEXT_END$", normalize(text))
        if declared != [candidate_hash] or len(blocks) != 1 or normalize(blocks[0]) != normalize(candidate.read_text(encoding="utf-8-sig")):
            raise transport.InputError("Temporary Markdown must contain this exact candidate and its SHA-256.")
    old = state["sources"].get(key)
    if old and old.get("role") != role:
        raise transport.InputError("A source key cannot change its role.")
    if adopt_rubric_id:
        if role != "RUBRIC" or old:
            raise transport.InputError("Adoption is only for the initially configured rubric ID.")
        details, _ = await cli.call("adopt-get", ["get", adopt_rubric_id, "-n", state["notebook_id"], "--json"])
        details = details.get("source", details)
        title = details.get("title", "")
        if not re.fullmatch(r"Technical Scientific Paper Revision Rubric v[0-9.]+", title):
            raise transport.InputError("The explicitly selected source is not the operational rubric.")
        _, verification = await fetch_verified(cli, state["notebook_id"], adopt_rubric_id, title)
        old = {"role": "RUBRIC", "managed_by": state["owner_id"], "adopted_rubric": True,
               "source_id": adopt_rubric_id, "title": title, "verification_file": verification,
               "verification_sha256": sha(Path(verification).read_bytes())}
        state["sources"][key] = old
        save_state(state_path, state)
    if old and old.get("content_sha256") == sha(raw):
        try:
            _, verification = await fetch_verified(cli, state["notebook_id"], old["source_id"], old["title"], text)
        except transport.InputError:
            old["verification_status"] = "STALE"
            save_state(state_path, state)
            raise
        old.update(content_file=str(file.resolve()), candidate_sha256=candidate_hash,
                   candidate_file=str(candidate.resolve()) if candidate else None,
                   verification_file=verification, verification_sha256=sha(Path(verification).read_bytes()),
                   verification_status="READY", verified_at=datetime.now(timezone.utc).isoformat())
        save_state(state_path, state)
        return {"status": "UNCHANGED", "source": old}
    title = f"APR__{state['owner_id']}__{key}__{sha(raw)[:12]}__{uuid.uuid4().hex[:8]}"
    upload = literal_upload(text)
    pending = {"key": key, "title": title, "content_sha256": sha(raw), "role": role,
               "upload_format": "literal-fence/v1", "upload_sha256": sha(upload.encode("utf-8"))}
    state["pending"].append(pending)
    save_state(state_path, state)  # Preserve an attempted write even if add returns no ID.
    added, add_receipt = await cli.call("add", ["add", "-", "--type", "text", "--title", title,
                                               "-n", state["notebook_id"], "--json"], upload)
    source_id = added.get("source", added).get("id")
    try:
        uuid.UUID(source_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise transport.InputError("Add returned no full source UUID; inspect its receipt before retrying.") from exc
    pending.update(source_id=source_id, add_receipt=add_receipt)
    save_state(state_path, state)
    await cli.call("wait", ["wait", source_id, "-n", state["notebook_id"], "--timeout", "45", "--json"])
    _, verification = await fetch_verified(cli, state["notebook_id"], source_id, title, text)
    entry = {"key": key, "role": role, "managed_by": state["owner_id"], "source_id": source_id, "title": title,
             "content_file": str(file.resolve()), "content_sha256": sha(raw),
             "candidate_sha256": candidate_hash, "add_receipt": add_receipt,
             "upload_format": pending["upload_format"], "upload_sha256": pending["upload_sha256"],
             "candidate_file": str(candidate.resolve()) if candidate else None,
             "verification_file": verification, "verification_sha256": sha(Path(verification).read_bytes()),
             "verification_status": "READY", "verified_at": datetime.now(timezone.utc).isoformat()}
    state["sources"][key] = entry
    state["pending"].remove(pending)
    if old:
        state["pending"].append({"key": key, "retire": old})
    save_state(state_path, state)  # New source is current before old-source retirement.
    if old:
        await retire(cli, state, old)
        state["pending"] = [item for item in state["pending"] if item.get("retire") != old]
        save_state(state_path, state)
    return {"status": "SYNCED", "source": entry}


async def verify_current(cli: CLI, path: Path, state: dict, key: str) -> dict:
    entry = state["sources"].get(key)
    if not entry:
        raise transport.InputError("Unknown source key.")
    try:
        content = Path(entry["content_file"])
        if sha(content.read_bytes()) != entry["content_sha256"]:
            raise transport.InputError("Local source content changed; synchronize a new version.")
        if entry.get("candidate_file") and sha(Path(entry["candidate_file"]).read_bytes()) != entry["candidate_sha256"]:
            raise transport.InputError("Candidate changed; the temporary source is stale.")
        _, verification = await fetch_verified(cli, state["notebook_id"], entry["source_id"], entry["title"], content.read_text(encoding="utf-8-sig"))
    except (transport.InputError, OSError):
        entry["verification_status"] = "STALE"
        save_state(path, state)
        raise
    entry.update(verification_file=verification, verification_sha256=sha(Path(verification).read_bytes()),
                 verification_status="READY", verified_at=datetime.now(timezone.utc).isoformat())
    save_state(path, state)
    return {"status": "VERIFIED", "source": entry}


async def cleanup(cli: CLI, path: Path, state: dict, key: str, approval_file: Path) -> dict:
    entry = state["sources"].get(key)
    if not entry or entry.get("role") != "TEMPORARY":
        raise transport.InputError("Cleanup is only for an existing temporary source; rubrics remain persistent.")
    if sha(Path(entry["candidate_file"]).read_bytes()) != entry.get("candidate_sha256") or sha(Path(entry["content_file"]).read_bytes()) != entry.get("content_sha256"):
        raise transport.InputError("Local text changed; approval/source binding is stale.")
    approval = read_json(approval_file)
    decision = approval.get("user_draft_decision", approval.get("author_approval", {}))
    if (decision.get("status") != "APPROVED" or not decision.get("evidence", "").strip()
            or decision.get("candidate_sha256") != entry.get("candidate_sha256")):
        raise transport.InputError("Cleanup needs the recorded author's approval of this exact candidate, not a notebook PASS.")
    entry = dict(entry, completion_approval_file=str(approval_file.resolve()),
                 completion_approval_sha256=sha(approval_file.read_bytes()))
    await retire(cli, state, entry)
    del state["sources"][key]
    save_state(path, state)
    return {"status": "REMOVED", "source_id": entry["source_id"]}


async def run(args: argparse.Namespace) -> dict:
    config = transport.load_config(args.config)
    notebook = transport.resolve_notebook(args.notebook, config)
    uuid.UUID(notebook)  # Never pass an ambiguous notebook prefix to a mutation.
    path = Path(args.state).resolve()
    with state_lock(path):
        state = load_state(path, notebook)
        cli = CLI(transport.cli_prefix(args, config), path.parent / "source-receipts")
        if args.command == "sync":
            return await sync(cli, path, state, args.key, Path(args.file), args.role,
                              Path(args.candidate) if args.candidate else None, args.adopt_rubric_id)
        if args.command == "cleanup":
            return await cleanup(cli, path, state, args.key, Path(args.approval_file))
        return await verify_current(cli, path, state, args.key)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config", "python", "profile", "storage", "backend"):
        parser.add_argument(f"--{name}")
    parser.add_argument("--notebook", required=True)
    parser.add_argument("--state", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    upload = sub.add_parser("sync")
    upload.add_argument("--key", required=True)
    upload.add_argument("--file", required=True)
    upload.add_argument("--role", choices=("RUBRIC", "TEMPORARY"), required=True)
    upload.add_argument("--candidate")
    upload.add_argument("--adopt-rubric-id", help="Explicit full ID of the existing operational rubric at bootstrap")
    verify = sub.add_parser("verify")
    verify.add_argument("--key", required=True)
    remove = sub.add_parser("cleanup")
    remove.add_argument("--key", required=True)
    remove.add_argument("--approval-file", required=True)
    try:
        result = asyncio.run(run(parser.parse_args()))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (transport.InputError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
