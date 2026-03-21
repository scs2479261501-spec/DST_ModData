from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from comment_text_analysis import build_group_summary, compare_keywords, load_comments_rows
    from steam_workshop import ensure_directory, utc_now_iso, write_manifest
else:
    from .comment_text_analysis import build_group_summary, compare_keywords, load_comments_rows
    from .steam_workshop import ensure_directory, utc_now_iso, write_manifest


LOGGER = logging.getLogger(__name__)

GROUP_SUMMARY_FIELDS = ["rank_group", "comment_count", "mod_count"]
LEFT_GROUP = "top_100"
RIGHT_GROUP = "rank_300_500"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze public workshop comments for top-vs-mid subscription groups."
    )
    parser.add_argument("--batch-id", required=True, help="Comment collection batch id to analyze.")
    parser.add_argument(
        "--min-comment-count",
        type=int,
        default=8,
        help="Minimum combined comment-document count for a keyword to be kept.",
    )
    parser.add_argument(
        "--top-keywords",
        type=int,
        default=25,
        help="Number of dominant keywords to export per group.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Python logging level.",
    )
    return parser


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    repo_root = Path(__file__).resolve().parents[1]
    processed_root = repo_root / "data" / "processed" / "steam_workshop" / args.batch_id
    comments_csv_path = processed_root / "top_comments.csv"
    comments_jsonl_path = processed_root / "top_comments.jsonl"
    if not comments_csv_path.exists() and not comments_jsonl_path.exists():
        parser.error(f"Comments inputs not found: {comments_csv_path}")

    analysis_root = repo_root / "data" / "processed" / "analysis"
    group_summary_path = analysis_root / f"comment_group_summary_{args.batch_id}.csv"
    keyword_comparison_path = analysis_root / f"comment_keyword_comparison_{args.batch_id}.csv"
    top_keywords_path = analysis_root / f"comment_keywords_{LEFT_GROUP}_{args.batch_id}.csv"
    mid_keywords_path = analysis_root / f"comment_keywords_{RIGHT_GROUP}_{args.batch_id}.csv"
    manifest_path = analysis_root / f"comment_text_analysis_manifest_{args.batch_id}.json"

    rows = load_comments_rows(comments_csv_path, fallback_jsonl_path=comments_jsonl_path)
    LOGGER.info("Loaded %s comment rows from %s", len(rows), comments_csv_path)

    group_summary_rows = build_group_summary(rows, [LEFT_GROUP, RIGHT_GROUP])
    comparison_rows = compare_keywords(
        rows,
        left_group=LEFT_GROUP,
        right_group=RIGHT_GROUP,
        min_comment_count=args.min_comment_count,
    )
    if not comparison_rows:
        raise ValueError("No keyword comparison rows were produced. Lower --min-comment-count or inspect the input data.")

    comparison_fieldnames = list(comparison_rows[0].keys())
    write_csv(group_summary_path, group_summary_rows, GROUP_SUMMARY_FIELDS)
    write_csv(keyword_comparison_path, comparison_rows, comparison_fieldnames)

    top_keywords = [row for row in comparison_rows if row["dominant_group"] == LEFT_GROUP][: args.top_keywords]
    mid_keywords = [row for row in comparison_rows if row["dominant_group"] == RIGHT_GROUP][: args.top_keywords]
    write_csv(top_keywords_path, top_keywords, comparison_fieldnames)
    write_csv(mid_keywords_path, mid_keywords, comparison_fieldnames)

    write_manifest(
        manifest_path,
        {
            "batch_id": args.batch_id,
            "analyzed_at_utc": utc_now_iso(),
            "inputs": {
                "comments_csv": str(comments_csv_path.relative_to(repo_root)),
                "comments_jsonl": str(comments_jsonl_path.relative_to(repo_root)),
            },
            "parameters": {
                "left_group": LEFT_GROUP,
                "right_group": RIGHT_GROUP,
                "min_comment_count": args.min_comment_count,
                "top_keywords": args.top_keywords,
            },
            "counts": {
                "comments_loaded": len(rows),
                "keywords_retained": len(comparison_rows),
                "left_group_keywords_exported": len(top_keywords),
                "right_group_keywords_exported": len(mid_keywords),
            },
            "outputs": {
                "group_summary_csv": str(group_summary_path.relative_to(repo_root)),
                "keyword_comparison_csv": str(keyword_comparison_path.relative_to(repo_root)),
                "left_group_keywords_csv": str(top_keywords_path.relative_to(repo_root)),
                "right_group_keywords_csv": str(mid_keywords_path.relative_to(repo_root)),
            },
        },
    )
    LOGGER.info("Keyword comparison written to %s", keyword_comparison_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
