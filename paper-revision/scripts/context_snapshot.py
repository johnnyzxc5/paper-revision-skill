"""Hash explicitly declared inputs to avoid redundant reads; no semantic certification."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def fingerprint(path: Path) -> dict:
    before = path.stat()
    if not path.is_file():
        raise ValueError(f'Not a regular file: {path}')
    sha = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            sha.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f'Input changed during hashing: {path}')
    return {'sha256': sha.hexdigest(), 'bytes': after.st_size}


def capture(root: Path, names: list[str]) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir() or not names:
        raise ValueError('A directory root and at least one declared file are required.')
    records, seen = [], set()
    for name in names:
        path = (root / name).resolve(strict=True)
        if path in seen:
            raise ValueError(f'Duplicate input: {name}')
        seen.add(path)
        try:
            display = path.relative_to(root).as_posix()
        except ValueError:
            display = str(path)
        records.append({'path': display, **fingerprint(path)})
    return {
        'schema_version': 1, 'root': str(root),
        'captured_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Declared local files only; no remote or semantic verification.',
        'files': records,
    }


def check(snapshot: dict, root_override: Path | None = None) -> dict:
    if not isinstance(snapshot, dict) or snapshot.get('schema_version') != 1:
        raise ValueError('Unsupported snapshot schema.')
    root_value = snapshot.get('root')
    if not isinstance(root_value, str) or not Path(root_value).is_absolute():
        raise ValueError('Snapshot root must be absolute.')
    root = Path(root_value)
    if root_override is not None:
        root = root_override.resolve(strict=True)
        if not root.is_dir():
            raise ValueError('Replacement root must be a directory.')
    records = snapshot.get('files')
    if not isinstance(records, list) or not records:
        raise ValueError('Snapshot requires nonempty file records.')
    seen, changed, missing, errors = set(), [], [], []
    for entry in records:
        if not isinstance(entry, dict):
            raise ValueError('Malformed file record.')
        name, digest, size = entry.get('path'), entry.get('sha256'), entry.get('bytes')
        if (not isinstance(name, str) or not name or
                not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest) or
                type(size) is not int or size < 0):
            raise ValueError('Malformed file path, digest or byte count.')
        path = (root / name).resolve()
        if not Path(name).is_absolute() and not path.is_relative_to(root.resolve()):
            raise ValueError('Relative file record escapes the snapshot root.')
        if path in seen:
            raise ValueError('Duplicate resolved file record.')
        seen.add(path)
        try:
            actual = fingerprint(path)
            if actual != {'sha256': digest, 'bytes': size}:
                changed.append(name)
        except FileNotFoundError:
            missing.append(name)
        except (OSError, ValueError) as exc:
            errors.append({'path': name, 'error': str(exc)})
    return {
        'status': 'STALE' if changed or missing or errors else 'UNCHANGED',
        'checked_files': len(records), 'changed': changed, 'missing': missing,
        'errors': errors, 'semantic_verification': False,
        'effective_root': str(root), 'root_overridden': root_override is not None,
    }


def write_snapshot(manifest: Path, snapshot: dict) -> None:
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open('x', encoding='utf-8', newline='\n') as target:
        json.dump(snapshot, target, ensure_ascii=False, indent=2)
        target.write('\n')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='command', required=True)
    create = modes.add_parser('capture')
    create.add_argument('--root', default='.')
    create.add_argument('--manifest', required=True)
    create.add_argument('--file', action='append', required=True)
    verify = modes.add_parser('check')
    verify.add_argument('--manifest', required=True)
    verify.add_argument('--root', help='Explicit root override; never modifies the manifest.')
    relocate = modes.add_parser('rebase', help='Verify relocation and save a new manifest.')
    relocate.add_argument('--manifest', required=True)
    relocate.add_argument('--root', required=True)
    relocate.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        manifest = Path(args.manifest)
        if args.command == 'capture':
            if manifest.exists():
                raise FileExistsError('Manifest exists; use a new revision path.')
            snapshot = capture(Path(args.root), args.file)
            write_snapshot(manifest, snapshot)
            result = {'status': 'CAPTURED', 'manifest': str(manifest.resolve()),
                      'files': len(snapshot['files']), 'semantic_verification': False}
        else:
            snapshot = json.loads(manifest.read_text(encoding='utf-8-sig'))
            root_override = Path(args.root) if args.root is not None else None
            if args.command == 'check':
                result = check(snapshot, root_override)
            else:
                output = Path(args.output)
                if output.exists() or output.resolve() == manifest.resolve():
                    raise FileExistsError('Output manifest exists; use a new revision path.')
                result = check(snapshot, root_override)
                if result['status'] == 'UNCHANGED':
                    # Preserve the original file paths, digests and capture time.
                    relocated = dict(snapshot)
                    relocated['root'] = result['effective_root']
                    relocated['rebased_utc'] = datetime.now(timezone.utc).isoformat()
                    relocated['rebased_from'] = {
                        'manifest': str(manifest.resolve()), 'root': snapshot['root'],
                    }
                    write_snapshot(output, relocated)
                    result = {'status': 'REBASED', 'manifest': str(output.resolve()),
                              'files': len(relocated['files']),
                              'semantic_verification': False}
        print(json.dumps(result, ensure_ascii=False, separators=(',', ':')))
        return 1 if result['status'] == 'STALE' else 0
    except (OSError, ValueError) as exc:
        print(json.dumps({'status': 'INVALID', 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
