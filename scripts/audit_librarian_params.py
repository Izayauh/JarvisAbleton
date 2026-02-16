#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


def collect_semantic_keys(reliable_params_path: Path):
    src = reliable_params_path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(src)

    mapping_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "SEMANTIC_PARAM_MAPPINGS":
                    mapping_node = node.value
                    break
                if isinstance(target, ast.Attribute) and target.attr == "SEMANTIC_PARAM_MAPPINGS":
                    mapping_node = node.value
                    break
        if mapping_node is not None:
            break

    if mapping_node is None:
        return set()

    try:
        mappings = ast.literal_eval(mapping_node)
    except Exception:
        return set()

    keys = set()
    if isinstance(mappings, dict):
        for plugin_map in mappings.values():
            if isinstance(plugin_map, dict):
                keys.update(plugin_map.keys())
    return keys


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from librarian.extractor import _normalize_plugin_params

    research_dir = root / "docs" / "Research"
    reliable_params = root / "ableton_controls" / "reliable_params.py"

    if not reliable_params.exists():
        print("Missing reliable_params.py")
        return 1

    known_keys = collect_semantic_keys(reliable_params)
    if not known_keys:
        print("Warning: No semantic mappings found.")

    json_files = sorted(research_dir.glob("*.json"))
    if not json_files:
        print("No JSON files found in docs/Research")
        return 0

    unknown = {}
    total_params = 0

    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Skipping {jf.name}: {e}")
            continue

        for sec_name, sec in (data.get("sections", {}) or {}).items():
            for device in sec.get("chain", []) or []:
                plugin = device.get("plugin", "")
                normalized = _normalize_plugin_params(plugin, device.get("key_params", {}) or {})
                for k in normalized.keys():
                    total_params += 1
                    if k not in known_keys:
                        unknown.setdefault(f"{plugin}:{k}", set()).add(jf.name)

    print(f"Scanned params: {total_params}")
    print(f"Known semantic keys: {len(known_keys)}")
    if not unknown:
        print("✅ No unknown parameter names found.")
        return 0

    print(f"⚠️ Unknown parameter names: {len(unknown)}")
    for k, files in sorted(unknown.items()):
        print(f"- {k}: {', '.join(sorted(files)[:5])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
