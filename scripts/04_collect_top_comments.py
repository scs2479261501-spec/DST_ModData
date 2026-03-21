from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pymysql

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from comment_text_analysis import rank_group_from_rank
    from steam_workshop import (
        COMMENTS_URL,
        attach_comment_metadata,
        create_session,
        ensure_directory,
        fetch_text,
        parse_workshop_comments_page,
        sleep_if_needed,
        utc_now_iso,
        write_manifest,
        write_text,
    )
else:
    from .comment_text_analysis import rank_group_from_rank
    from .steam_workshop import (
        COMMENTS_URL,
        attach_comment_metadata,
        create_session,
        ensure_directory,
        fetch_text,
        parse_workshop_comments_page,
        sleep_if_needed,
        utc_now_iso,
        write_manifest,
        write_text,
    )


LOGGER = logging.getLogger(__name__)

SELECTED_MOD_FIELDS = [
    "subscription_rank",
    "rank_group",
    "mod_id",
    "title",
    "subscriptions",
]

COMMENT_ANALYSIS_FIELDS = [
    "batch_id",
    "crawl_time_utc",
    "mod_id",
    "mod_title",
    "mod_subscriptions",
    "subscription_rank",
    "rank_group",
    "comment_page",
    "comment_id",
    "commenter_name",
    "commenter_profile_url",
    "commenter_steam_id",
    "commenter_miniprofile_id",
    "comment_timestamp_epoch",
    "comment_timestamp_utc",
    "comment_timestamp_text",
    "content_text",
    "content_html",
    "raw_comments_path",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect public workshop comments for the top-N DST mods ranked by subscriptions."
    )
    parser.add_argument("--top-n", type=int, default=500, help="Number of top-subscribed mods to fetch comments for.")
    parser.add_argument("--comment-pages", type=int, default=2, help="Maximum number of comment pages per mod.")
    parser.add_argument("--sleep-seconds", type=float, default=0.3, help="Delay between network requests.")
    parser.add_argument("--batch-id", default=None, help="Optional stable batch id.")
    parser.add_argument("--restart", action="store_true", help="Ignore existing checkpoint and restart the batch.")
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")))
    parser.add_argument("--user", default=os.getenv("MYSQL_USER", "root"))
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD", ""))
    parser.add_argument("--database", default=os.getenv("MYSQL_DATABASE", "steamDST"))
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Python logging level.",
    )
    return parser


def mysql_connection(args: argparse.Namespace) -> pymysql.Connection:
    return pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
    )


def fetch_top_mods(args: argparse.Namespace) -> tuple[str, list[dict[str, Any]]]:
    query = """
    WITH latest_batch AS (
        SELECT batch_id
        FROM steam_api_mods_raw
        GROUP BY batch_id
        ORDER BY MAX(crawl_time_utc) DESC, batch_id DESC
        LIMIT 1
    ), ranked_mods AS (
        SELECT
            mod_id,
            title,
            subscriptions,
            ROW_NUMBER() OVER (ORDER BY subscriptions DESC, mod_id ASC) AS subscription_rank
        FROM steam_api_mods_raw
        WHERE batch_id = (SELECT batch_id FROM latest_batch)
          AND subscriptions IS NOT NULL
    )
    SELECT
        (SELECT batch_id FROM latest_batch) AS source_api_batch,
        mod_id,
        COALESCE(title, '') AS title,
        subscriptions,
        subscription_rank
    FROM ranked_mods
    WHERE subscription_rank <= %s
    ORDER BY subscription_rank;
    """
    with mysql_connection(args) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (args.top_n,))
            rows = cursor.fetchall()
    if not rows:
        raise ValueError("No top mods were returned from steam_api_mods_raw.")
    source_api_batch = str(rows[0][0])
    mods: list[dict[str, Any]] = []
    for row in rows:
        subscription_rank = int(row[4])
        mods.append(
            {
                "subscription_rank": subscription_rank,
                "rank_group": rank_group_from_rank(subscription_rank),
                "mod_id": str(row[1]),
                "title": row[2] or "",
                "subscriptions": int(row[3]) if row[3] is not None else None,
            }
        )
    return source_api_batch, mods


def serialize_row(row: dict[str, Any], fieldnames: list[str]) -> dict[str, Any]:
    export_row: dict[str, Any] = {}
    for fieldname in fieldnames:
        value = row.get(fieldname)
        if isinstance(value, (list, dict)):
            export_row[fieldname] = json.dumps(value, ensure_ascii=False)
        elif value is None:
            export_row[fieldname] = ""
        else:
            export_row[fieldname] = value
    return export_row


def csv_has_expected_header(path: Path, fieldnames: list[str]) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        first_line = csv_file.readline().strip("\r\n")
    if not first_line:
        return False
    return first_line.split(",") == fieldnames


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(serialize_row(row, fieldnames))


def append_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    if not rows:
        return
    ensure_directory(path.parent)
    write_header = not csv_has_expected_header(path, fieldnames)
    with path.open("a", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow(serialize_row(row, fieldnames))


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    ensure_directory(path.parent)
    with path.open("a", encoding="utf-8") as jsonl_file:
        for row in rows:
            jsonl_file.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_checkpoint(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    if args.top_n < 1:
        parser.error("--top-n must be >= 1")
    if args.comment_pages < 1:
        parser.error("--comment-pages must be >= 1")
    if args.sleep_seconds < 0:
        parser.error("--sleep-seconds must be >= 0")

    repo_root = Path(__file__).resolve().parents[1]
    batch_id = args.batch_id or f"top500_comments_{utc_now_iso().replace(':', '').replace('-', '').replace('+00:00', 'Z')}"
    batch_crawl_time = utc_now_iso()

    raw_root = repo_root / "data" / "raw" / "steam_workshop" / batch_id
    processed_root = repo_root / "data" / "processed" / "steam_workshop" / batch_id
    comments_root = raw_root / "comments"
    checkpoint_path = raw_root / "checkpoint.json"
    selected_mods_path = processed_root / "selected_mods.csv"
    comments_csv_path = processed_root / "top_comments.csv"
    comments_jsonl_path = processed_root / "top_comments.jsonl"
    manifest_path = processed_root / "crawl_manifest.json"

    ensure_directory(comments_root)
    ensure_directory(processed_root)

    source_api_batch, top_mods = fetch_top_mods(args)
    write_csv(selected_mods_path, top_mods, SELECTED_MOD_FIELDS)

    checkpoint = None if args.restart else load_checkpoint(checkpoint_path)
    if checkpoint:
        if checkpoint.get("top_n") != args.top_n or checkpoint.get("comment_pages") != args.comment_pages:
            parser.error("Existing checkpoint parameters do not match this run. Use --restart or a new --batch-id.")
        start_index = int(checkpoint.get("next_index", 0))
        comments_collected = int(checkpoint.get("comments_collected", 0))
        failed_mods = list(checkpoint.get("failed_mods", []))
    else:
        start_index = 0
        comments_collected = 0
        failed_mods: list[dict[str, Any]] = []
        if comments_csv_path.exists():
            comments_csv_path.unlink()
        if comments_jsonl_path.exists():
            comments_jsonl_path.unlink()

    session = create_session()

    for mod_index in range(start_index, len(top_mods)):
        mod_info = top_mods[mod_index]
        mod_id = str(mod_info["mod_id"])
        subscription_rank = int(mod_info["subscription_rank"])
        LOGGER.info(
            "Fetching comments for mod %s (%s/%s, rank=%s)",
            mod_id,
            mod_index + 1,
            len(top_mods),
            subscription_rank,
        )

        per_mod_rows: list[dict[str, Any]] = []
        seen_comment_ids: set[str] = set()
        failure: dict[str, Any] | None = None
        comments_url = f"{COMMENTS_URL}{mod_id}"

        for comment_page in range(1, args.comment_pages + 1):
            params: dict[str, int] = {}
            if comment_page > 1:
                params["ctp"] = comment_page
            try:
                comments_html = fetch_text(session, comments_url, params=params or None)
            except Exception as exc:  # noqa: BLE001
                failure = {
                    "mod_id": mod_id,
                    "subscription_rank": subscription_rank,
                    "page": comment_page,
                    "error": str(exc),
                }
                LOGGER.warning("Failed to fetch comments for mod %s page %s: %s", mod_id, comment_page, exc)
                break

            comments_path = comments_root / f"{subscription_rank:04d}_{mod_id}_ctp_{comment_page}.html"
            write_text(comments_path, comments_html)
            parsed_comments = parse_workshop_comments_page(
                comments_html,
                mod_id=mod_id,
                comment_page=comment_page,
            )
            new_comments = [comment for comment in parsed_comments if comment["comment_id"] not in seen_comment_ids]
            if not new_comments:
                LOGGER.info("No new comments found for mod %s on page %s", mod_id, comment_page)
                break

            for comment in new_comments:
                seen_comment_ids.add(comment["comment_id"])
                enriched_comment = attach_comment_metadata(
                    comment,
                    batch_id=batch_id,
                    crawl_time_utc=batch_crawl_time,
                    raw_comments_path=str(comments_path.relative_to(repo_root)),
                )
                enriched_comment["mod_title"] = mod_info["title"]
                enriched_comment["mod_subscriptions"] = mod_info["subscriptions"]
                enriched_comment["subscription_rank"] = subscription_rank
                enriched_comment["rank_group"] = mod_info["rank_group"]
                per_mod_rows.append(enriched_comment)

            sleep_if_needed(args.sleep_seconds)

        append_csv(comments_csv_path, per_mod_rows, COMMENT_ANALYSIS_FIELDS)
        append_jsonl(comments_jsonl_path, per_mod_rows)
        comments_collected += len(per_mod_rows)
        if failure is not None:
            failed_mods.append(failure)

        checkpoint_payload = {
            "batch_id": batch_id,
            "source_api_batch": source_api_batch,
            "top_n": args.top_n,
            "comment_pages": args.comment_pages,
            "next_index": mod_index + 1,
            "completed_mods": mod_index + 1,
            "comments_collected": comments_collected,
            "failed_mods": failed_mods,
            "updated_at_utc": utc_now_iso(),
            "completed": mod_index + 1 >= len(top_mods),
        }
        save_checkpoint(checkpoint_path, checkpoint_payload)

    final_checkpoint = load_checkpoint(checkpoint_path) or {}
    write_manifest(
        manifest_path,
        {
            "batch_id": batch_id,
            "started_at_utc": batch_crawl_time,
            "completed_at_utc": utc_now_iso(),
            "source_method": "public_workshop_comments_top_n",
            "source_api_batch": source_api_batch,
            "crawl_parameters": {
                "top_n": args.top_n,
                "comment_pages": args.comment_pages,
                "sleep_seconds": args.sleep_seconds,
            },
            "counts": {
                "mods_selected": len(top_mods),
                "comments_collected": comments_collected,
                "failed_mods": len(failed_mods),
            },
            "outputs": {
                "selected_mods_csv": str(selected_mods_path.relative_to(repo_root)),
                "comments_csv": str(comments_csv_path.relative_to(repo_root)),
                "comments_jsonl": str(comments_jsonl_path.relative_to(repo_root)),
                "checkpoint": str(checkpoint_path.relative_to(repo_root)),
            },
            "failures": failed_mods,
            "checkpoint": final_checkpoint,
        },
    )
    LOGGER.info("Collected %s comments across %s mods", comments_collected, len(top_mods))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
