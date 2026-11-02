#!/usr/bin/env python3
"""Script to remove all non-blocking objects from all screens in project.yaml."""

import argparse
from pathlib import Path
from typing import Dict, List, Set
import yaml


def remove_non_blocking_objects(project_path: Path, objects_path: Path, dry_run: bool = False) -> int:
    with open(objects_path, "r", encoding="utf-8") as f:
        objects_data = yaml.safe_load(f)

    non_blocking_codes: Set[int] = set()
    non_blocking_names: Dict[int, str] = {}
    for obj in objects_data.get("objects", []):
        flags = obj.get("flags", {})
        is_blocking = flags.get("blocking", False)
        is_interactive = flags.get("interactive", False)
        is_secret = flags.get("secret", False)

        # Non-blocking objects: not blocking AND not interactive AND not secret
        if not is_blocking and not is_interactive and not is_secret:
            code = obj.get("code")
            if code is not None:
                non_blocking_codes.add(code)
                non_blocking_names[code] = obj.get("id", f"code_{code}")

    print(f"Identified {len(non_blocking_codes)} non-blocking object definitions.")

    with open(project_path, "r", encoding="utf-8") as f:
        project_data = yaml.safe_load(f)

    total_removed = 0
    screens = project_data.get("screens", [])
    for screen in screens:
        screen_id = screen.get("id", "UNKNOWN")
        orig_objects = screen.get("objects", [])
        filtered_objects = [o for o in orig_objects if o.get("code") not in non_blocking_codes]
        removed_count = len(orig_objects) - len(filtered_objects)
        if removed_count > 0:
            print(f"Screen {screen_id}: removed {removed_count} non-blocking objects ({len(orig_objects)} -> {len(filtered_objects)})")
            total_removed += removed_count
            screen["objects"] = filtered_objects

    print(f"\nTotal non-blocking objects removed across all screens: {total_removed}")

    if not dry_run and total_removed > 0:
        with open(project_path, "w", encoding="utf-8") as f:
            yaml.dump(project_data, f, sort_keys=False, indent=2, allow_unicode=True)
        print(f"Successfully saved updated project to {project_path}")
    elif dry_run:
        print("Dry run completed. No files modified.")

    return total_removed


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove non-blocking objects from project screens.")
    parser.add_argument("--project", "-p", type=Path, default=Path("world/project.yaml"), help="Path to project.yaml")
    parser.add_argument("--objects", "-o", type=Path, default=Path("world/objects.yaml"), help="Path to objects.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without modifying files")

    args = parser.parse_args()
    remove_non_blocking_objects(args.project, args.objects, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

