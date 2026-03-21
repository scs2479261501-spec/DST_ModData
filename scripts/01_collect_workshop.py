from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from steam_workshop import (
        BROWSE_URL,
        COMMENTS_URL,
        DETAIL_URL,
        COMMENT_EXPORT_FIELDS,
        MOD_EXPORT_FIELDS,
        WORKSHOP_APP_ID,
        attach_comment_metadata,
        create_session,
        ensure_directory,
        fetch_text,
        log_summary,
        merge_discovery_and_detail,
        parse_workshop_browse_page,
        parse_workshop_comments_page,
        parse_workshop_detail_page,
        sleep_if_needed,
        utc_now_iso,
        write_csv_rows,
        write_jsonl_rows,
        write_manifest,
        write_text,
    )
else:
    from .steam_workshop import (
        BROWSE_URL,
        COMMENTS_URL,
        DETAIL_URL,
        COMMENT_EXPORT_FIELDS,
        MOD_EXPORT_FIELDS,
        WORKSHOP_APP_ID,
        attach_comment_metadata,
        create_session,
        ensure_directory,
        fetch_text,
        log_summary,
        merge_discovery_and_detail,
        parse_workshop_browse_page,
        parse_workshop_comments_page,
        parse_workshop_detail_page,
        sleep_if_needed,
        utc_now_iso,
        write_csv_rows,
        write_jsonl_rows,
        write_manifest,
        write_text,
    )


LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect a reproducible DST Workshop sample from public Steam pages."
    )
    parser.add_argument("--pages", type=int, default=1, help="Number of browse pages to crawl.")
    parser.add_argument(
        "--max-items",
        type=int,
        default=5,
        help="Maximum number of workshop items to collect details for.",
    )
    parser.add_argument(
        "--fetch-comments",
        action="store_true",
        help="Fetch public workshop comments for the collected items.",
    )
    parser.add_argument(
        "--comment-item-limit",
        type=int,
        default=2,
        help="Maximum number of items to fetch comment pages for.",
    )
    parser.add_argument(
        "--comment-pages",
        type=int,
        default=1,
        help="Maximum number of comment pages to request per item.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="Delay between network requests.",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Optional stable batch id. If omitted, a UTC timestamp is used.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Python logging level.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    if args.pages < 1:
        parser.error("--pages must be >= 1")
    if args.max_items < 1:
        parser.error("--max-items must be >= 1")
    if args.comment_pages < 1:
        parser.error("--comment-pages must be >= 1")
    if args.comment_item_limit < 0:
        parser.error("--comment-item-limit must be >= 0")

    repo_root = Path(__file__).resolve().parents[1]
    batch_id = args.batch_id or utc_now_iso().replace(":", "").replace("-", "").replace("+00:00", "Z")
    batch_crawl_time = utc_now_iso()

    raw_root = repo_root / "data" / "raw" / "steam_workshop" / batch_id
    processed_root = repo_root / "data" / "processed" / "steam_workshop" / batch_id
    browse_root = raw_root / "browse"
    detail_root = raw_root / "details"
    comments_root = raw_root / "comments"

    ensure_directory(browse_root)
    ensure_directory(detail_root)
    ensure_directory(comments_root)
    ensure_directory(processed_root)

    session = create_session()
    discovered_items: list[dict[str, object]] = []
    browse_page_summaries: list[dict[str, object]] = []

    for page_number in range(1, args.pages + 1):
        browse_params = {
            "appid": WORKSHOP_APP_ID,
            "browsesort": "trend",
            "section": "readytouseitems",
            "actualsort": "trend",
            "p": page_number,
            "days": -1,
        }
        LOGGER.info("Fetching browse page %s", page_number)
        browse_html = fetch_text(session, BROWSE_URL, params=browse_params)
        browse_path = browse_root / f"browse_page_{page_number:04d}.html"
        write_text(browse_path, browse_html)

        browse_summary = parse_workshop_browse_page(
            browse_html,
            source_url=f"{BROWSE_URL}?appid={WORKSHOP_APP_ID}&p={page_number}",
            page_number=page_number,
        )
        browse_page_summaries.append(
            {
                "page_number": browse_summary["page_number"],
                "range_start": browse_summary["range_start"],
                "range_end": browse_summary["range_end"],
                "total_entries": browse_summary["total_entries"],
                "items_found": len(browse_summary["items"]),
                "raw_browse_path": str(browse_path.relative_to(repo_root)),
            }
        )

        for item in browse_summary["items"]:
            if len(discovered_items) >= args.max_items:
                break
            discovered_items.append(item)

        if len(discovered_items) >= args.max_items:
            break

        sleep_if_needed(args.sleep_seconds)

    mod_rows: list[dict[str, object]] = []
    comment_rows: list[dict[str, object]] = []

    for item_index, discover_item in enumerate(discovered_items, start=1):
        mod_id = str(discover_item["mod_id"])
        detail_source_url = f"{DETAIL_URL}?id={mod_id}"
        LOGGER.info("Fetching detail page for mod %s (%s/%s)", mod_id, item_index, len(discovered_items))

        detail_html = fetch_text(session, DETAIL_URL, params={"id": mod_id})
        detail_path = detail_root / f"{mod_id}.html"
        write_text(detail_path, detail_html)

        detail_record = parse_workshop_detail_page(detail_html, source_url=detail_source_url)
        mod_rows.append(
            merge_discovery_and_detail(
                discover_item,
                detail_record,
                batch_id=batch_id,
                crawl_time_utc=batch_crawl_time,
                raw_detail_path=str(detail_path.relative_to(repo_root)),
            )
        )

        sleep_if_needed(args.sleep_seconds)

        if not args.fetch_comments or item_index > args.comment_item_limit:
            continue

        seen_comment_ids: set[str] = set()
        comments_url = f"{COMMENTS_URL}{mod_id}"
        for comment_page in range(1, args.comment_pages + 1):
            LOGGER.info("Fetching comments page %s for mod %s", comment_page, mod_id)
            comment_params: dict[str, int] = {}
            if comment_page > 1:
                comment_params["ctp"] = comment_page

            comments_html = fetch_text(session, comments_url, params=comment_params or None)
            comments_path = comments_root / f"{mod_id}_ctp_{comment_page}.html"
            write_text(comments_path, comments_html)

            parsed_comments = parse_workshop_comments_page(
                comments_html,
                mod_id=mod_id,
                comment_page=comment_page,
            )
            new_comments = [comment for comment in parsed_comments if comment["comment_id"] not in seen_comment_ids]
            if not new_comments:
                LOGGER.info("No new comments found for mod %s on comments page %s", mod_id, comment_page)
                break

            for comment in new_comments:
                seen_comment_ids.add(comment["comment_id"])
                comment_rows.append(
                    attach_comment_metadata(
                        comment,
                        batch_id=batch_id,
                        crawl_time_utc=batch_crawl_time,
                        raw_comments_path=str(comments_path.relative_to(repo_root)),
                    )
                )

            sleep_if_needed(args.sleep_seconds)

    mods_csv_path = processed_root / "mods.csv"
    mods_jsonl_path = processed_root / "mods.jsonl"
    comments_csv_path = processed_root / "comments.csv"
    comments_jsonl_path = processed_root / "comments.jsonl"
    manifest_path = processed_root / "crawl_manifest.json"

    write_csv_rows(mods_csv_path, mod_rows, MOD_EXPORT_FIELDS)
    write_jsonl_rows(mods_jsonl_path, mod_rows)
    write_csv_rows(comments_csv_path, comment_rows, COMMENT_EXPORT_FIELDS)
    write_jsonl_rows(comments_jsonl_path, comment_rows)

    write_manifest(
        manifest_path,
        {
            "batch_id": batch_id,
            "started_at_utc": batch_crawl_time,
            "completed_at_utc": utc_now_iso(),
            "source_method": "public_workshop_html",
            "api_status": "Steam Web API QueryFiles requires a key and was not used in this batch.",
            "crawl_parameters": {
                "pages": args.pages,
                "max_items": args.max_items,
                "fetch_comments": args.fetch_comments,
                "comment_item_limit": args.comment_item_limit,
                "comment_pages": args.comment_pages,
                "sleep_seconds": args.sleep_seconds,
            },
            "browse_pages": browse_page_summaries,
            "counts": {
                "items_discovered": len(discovered_items),
                "mods_collected": len(mod_rows),
                "comments_collected": len(comment_rows),
            },
            "outputs": {
                "mods_csv": str(mods_csv_path.relative_to(repo_root)),
                "mods_jsonl": str(mods_jsonl_path.relative_to(repo_root)),
                "comments_csv": str(comments_csv_path.relative_to(repo_root)),
                "comments_jsonl": str(comments_jsonl_path.relative_to(repo_root)),
            },
        },
    )

    log_summary(mod_rows, comment_rows)
    LOGGER.info("Batch output written to %s", processed_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
