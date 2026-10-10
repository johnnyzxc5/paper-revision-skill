#!/usr/bin/env python3
"""Select writing-notebook sources deterministically from task profiles."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable


DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "references" / "writing-source-routing.json"


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def normalize_title(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"[.]pdf$", "", value)
    value = value.replace("_", " ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def walk_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_objects(child)


def inventory_pairs(document: Any) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in walk_objects(document):
        title = next(
            (item.get(key) for key in ("title", "name", "source_title") if nonempty_string(item.get(key))),
            None,
        )
        source_id = next(
            (item.get(key) for key in ("source_id", "id") if nonempty_string(item.get(key))),
            None,
        )
        if title and source_id:
            pair = (title.strip(), source_id.strip())
            if pair not in pairs:
                pairs.append(pair)
    return pairs


def validate_registry(registry: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(registry, dict) or registry.get("schema_version") != 1:
        return ["Registry root must be schema_version 1."]
    sources = registry.get("sources")
    profiles = registry.get("profiles")
    if not isinstance(sources, dict) or not sources:
        errors.append("Registry sources must be a non-empty object.")
        sources = {}
    if not isinstance(profiles, dict) or not profiles:
        errors.append("Registry profiles must be a non-empty object.")
        profiles = {}
    for key, source in sources.items():
        if not isinstance(source, dict) or not nonempty_string(source.get("canonical_title")):
            errors.append(f"Source {key!r} requires canonical_title.")
    for name, profile in profiles.items():
        if not isinstance(profile, dict):
            errors.append(f"Profile {name!r} must be an object.")
            continue
        for field in ("layers", "required", "optional"):
            values = profile.get(field)
            if not isinstance(values, list) or not all(nonempty_string(value) for value in values):
                errors.append(f"Profile {name!r}.{field} must be an array of strings.")
        for source_key in profile.get("required", []) + profile.get("optional", []):
            if source_key not in sources:
                errors.append(f"Profile {name!r} references unknown source {source_key!r}.")
    return errors


def resolve_sources(
    source_keys: list[str],
    sources: dict[str, Any],
    inventory: Any | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    resolved: list[dict[str, Any]] = []
    errors: list[str] = []
    pairs = inventory_pairs(inventory) if inventory is not None else []
    for key in source_keys:
        source = sources[key]
        item = {
            "source_key": key,
            "title": source["canonical_title"],
            "authority": source.get("authority"),
            "description": source.get("description"),
        }
        if inventory is not None:
            aliases = [source["canonical_title"], *source.get("title_aliases", [])]
            normalized_aliases = {normalize_title(alias) for alias in aliases}
            matches = [
                {"title": title, "source_id": source_id}
                for title, source_id in pairs
                if normalize_title(title) in normalized_aliases
            ]
            if len(matches) == 1:
                item.update(matches[0])
            elif not matches:
                errors.append(f"Required source {key!r} is absent from the supplied inventory.")
            else:
                errors.append(f"Required source {key!r} is ambiguous in the supplied inventory.")
                item["matches"] = matches
        resolved.append(item)
    return resolved, errors


def route(request: Any, registry: Any, inventory: Any | None = None) -> dict[str, Any]:
    errors = validate_registry(registry)
    warnings: list[str] = []
    if not isinstance(request, dict) or request.get("schema_version") != 1:
        errors.append("Request root must be schema_version 1.")
        request = {}
    if not nonempty_string(request.get("task_id")):
        errors.append("task_id is required.")
    profile_names = request.get("profiles")
    if not isinstance(profile_names, list) or not profile_names or not all(
        nonempty_string(name) for name in profile_names
    ):
        errors.append("profiles must be a non-empty array of strings.")
        profile_names = []
    profile_names = unique(profile_names)

    profiles = registry.get("profiles", {}) if isinstance(registry, dict) else {}
    sources = registry.get("sources", {}) if isinstance(registry, dict) else {}
    unknown = [name for name in profile_names if name not in profiles]
    if unknown:
        errors.append(f"Unknown profiles: {', '.join(unknown)}.")

    selected_profiles = [profiles[name] for name in profile_names if name in profiles]
    venue_profile = request.get("venue_profile", "UNKNOWN")
    if not nonempty_string(venue_profile):
        errors.append("venue_profile must be a non-empty string when supplied.")
        venue_profile = "UNKNOWN"
    if any(name.startswith("ieee_") for name in profile_names) and not re.match(
        r"(?i)^IEEE(?:\b|$)", venue_profile.strip()
    ):
        errors.append("IEEE profiles require an explicitly activated IEEE venue_profile.")
    if isinstance(inventory, dict) and "status" in inventory and inventory["status"] != "success":
        errors.append("The supplied source inventory is not a successful wrapper result.")
    required = unique(
        source_key
        for profile in selected_profiles
        for source_key in profile.get("required", [])
    )
    if selected_profiles and registry.get("policy", {}).get("rubric_required_for_profiles"):
        rubric_key = registry.get("rubric_source_key")
        if rubric_key and rubric_key not in required:
            required.insert(0, rubric_key)
    optional = [
        key
        for key in unique(
            source_key
            for profile in selected_profiles
            for source_key in profile.get("optional", [])
        )
        if key not in required
    ]
    expected_layers = unique(
        layer for profile in selected_profiles for layer in profile.get("layers", [])
    )
    declared_layers = request.get("declared_layers", [])
    if not isinstance(declared_layers, list) or not all(nonempty_string(layer) for layer in declared_layers):
        errors.append("declared_layers must be an array of strings.")
        declared_layers = []
    missing_layers = [layer for layer in expected_layers if layer not in declared_layers]
    if missing_layers:
        errors.append("declared_layers omit profile layers: " + ", ".join(missing_layers) + ".")
    extra_layers = [layer for layer in declared_layers if layer not in expected_layers]
    if extra_layers:
        warnings.append("declared_layers include layers not implied by profiles: " + ", ".join(extra_layers) + ".")

    max_sources = registry.get("policy", {}).get("max_required_sources_per_query", 5)
    split_required = isinstance(max_sources, int) and len(required) > max_sources
    if split_required:
        warnings.append(
            f"Atomic query requires {len(required)} sources, above the limit {max_sources}; split by profile."
        )

    resolved_required, resolution_errors = resolve_sources(required, sources, inventory)
    binding = request.get("rubric_binding")
    if binding:
        try:
            import writing_review_guard as writing_reviews
            rubric = writing_reviews.verified_source(Path(binding["state_file"]), binding["key"],
                Path(binding["file"]), binding["notebook_id"])
            if rubric.get("role") != "RUBRIC":
                raise ValueError("Binding is not a persistent rubric.")
            matching = [pair for pair in inventory_pairs(inventory) if pair == (rubric["title"], rubric["source_id"])]
            if len(matching) != 1:
                raise ValueError("Verified rubric ID/title is absent from the supplied live inventory.")
            rubric_key = registry.get("rubric_source_key")
            resolution_errors = [error for error in resolution_errors if f"{rubric_key!r}" not in error]
            for item in resolved_required:
                if item["source_key"] == rubric_key:
                    item.update(title=rubric["title"], source_id=rubric["source_id"], content_verified=True)
                    item.pop("matches", None)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            resolution_errors.append(f"Invalid/stale rubric_binding: {exc}")
    else:
        warnings.append("Rubric title matching alone does not establish current content; new exact-text reviews require a verified rubric_binding.")
    errors.extend(resolution_errors)
    optional_items, _ = resolve_sources(optional, sources, None)
    for item in resolved_required:
        item["required_by_profiles"] = [
            name
            for name in profile_names
            if name in profiles and item["source_key"] in profiles[name].get("required", [])
        ]
    for item in optional_items:
        item["optional_for_profiles"] = [
            name
            for name in profile_names
            if name in profiles and item["source_key"] in profiles[name].get("optional", [])
        ]

    status = "INVALID" if errors else "SPLIT_REQUIRED" if split_required else "READY"
    return {
        "schema": "writing-source-router/1.0",
        "status": status,
        "task_id": request.get("task_id"),
        "profiles": profile_names,
        "venue_profile": venue_profile,
        "profile_descriptions": {
            name: profiles[name].get("description") for name in profile_names if name in profiles
        },
        "declared_layers": declared_layers,
        "expected_layers": expected_layers,
        "required_sources": resolved_required,
        "optional_sources": optional_items,
        "coverage_gaps": registry.get("coverage_gaps", []),
        "split_required": split_required,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Route an academic writing query to NotebookLM sources")
    parser.add_argument("request", help="Path to writing-source request JSON")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--inventory", help="Optional JSON output from `notebooklm_tool.py sources -n writing`")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        request = json.loads(Path(args.request).read_text(encoding="utf-8-sig"))
        registry = json.loads(Path(args.registry).read_text(encoding="utf-8-sig"))
        inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8-sig")) if args.inventory else None
        result = route(request, registry, inventory)
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None), flush=True)
        return 0 if result["status"] in {"READY", "SPLIT_REQUIRED"} else 1
    except (OSError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "schema": "writing-source-router/1.0",
                    "status": "ERROR",
                    "errors": [f"{type(exc).__name__}: {exc}"],
                    "warnings": [],
                },
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            ),
            flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
