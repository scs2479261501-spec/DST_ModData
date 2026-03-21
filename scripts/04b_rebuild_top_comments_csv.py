from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from comment_text_analysis import EXPECTED_COMMENT_FIELDS
    from steam_workshop import ensure_directory
else:
    from .comment_text_analysis import EXPECTED_COMMENT_FIELDS
    from .steam_workshop import ensure_directory


LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rebuild top_comments.csv from top_comments.jsonl for a batch.")
    parser.add_argument("--batch-id", required=True, help="Comment collection batch id.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser


def serialize_row(payload: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for field in EXPECTED_COMMENT_FIELDS:
        value = payload.get(field)
        row[field] = "" if value is None else value
    return row


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    repo_root = Path(__file__).resolve().parents[1]
    processed_root = repo_root / "data" / "processed" / "steam_workshop" / args.batch_id
    jsonl_path = processed_root / "top_comments.jsonl"
    csv_path = processed_root / "top_comments.csv"
    if not jsonl_path.exists():
        parser.error(f"Comments JSONL not found: {jsonl_path}")

    ensure_directory(csv_path.parent)
    row_count = 0
    with jsonl_path.open("r", encoding="utf-8") as jsonl_file, csv_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=EXPECTED_COMMENT_FIELDS)
        writer.writeheader()
        for line in jsonl_file:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            writer.writerow(serialize_row(payload))
            row_count += 1

    LOGGER.info("Rebuilt %s with %s comment rows", csv_path, row_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
