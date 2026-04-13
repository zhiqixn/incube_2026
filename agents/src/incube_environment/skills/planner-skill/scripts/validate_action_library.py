#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
import sys


VALID_FAMILIES = {
    "move",
    "hold",
    "coordinate",
    "observe",
    "area_cover",
    "deliver",
    "recover",
    "pathfind",
    "relay",
    "track",
    "strike",
    "protect",
    "deceive",
    "sustain",
    "inspect",
}

REQUIRED_COLUMNS = {
    "id",
    "name",
    "aliases",
    "family",
    "summary",
    "commercial_scenarios",
    "defense_scenarios",
    "source_revision",
    "tags",
}


def main() -> int:
    skill_root = Path(__file__).resolve().parents[1]
    catalog_path = skill_root / "references" / "action_library.autonodyne.csv"

    with catalog_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])

        missing_columns = REQUIRED_COLUMNS - fieldnames
        if missing_columns:
            print(f"Missing columns: {sorted(missing_columns)}", file=sys.stderr)
            return 1

        ids = set()
        family_counts: Counter[str] = Counter()
        revision_counts: Counter[str] = Counter()
        rows = 0

        for row_number, row in enumerate(reader, start=2):
            rows += 1
            action_id = row["id"].strip()
            family = row["family"].strip()
            name = row["name"].strip()

            if not action_id or not name:
                print(f"Row {row_number}: action id and name are required", file=sys.stderr)
                return 1

            if action_id in ids:
                print(f"Row {row_number}: duplicate id '{action_id}'", file=sys.stderr)
                return 1
            ids.add(action_id)

            if family not in VALID_FAMILIES:
                print(f"Row {row_number}: invalid family '{family}'", file=sys.stderr)
                return 1

            for key in ("summary", "commercial_scenarios", "defense_scenarios", "source_revision", "tags"):
                if not row[key].strip():
                    print(f"Row {row_number}: column '{key}' must not be empty", file=sys.stderr)
                    return 1

            family_counts[family] += 1
            revision_counts[row["source_revision"].strip()] += 1

    print(f"Validated {rows} actions from {catalog_path.name}")
    print("Families:")
    for family, count in sorted(family_counts.items()):
        print(f"  {family}: {count}")
    print("Source revisions:")
    for revision, count in sorted(revision_counts.items()):
        print(f"  {revision}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
