from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from steam_api import (
        API_EXPORT_FIELDS,
        DEFAULT_CURSOR,
        append_csv_rows,
        append_jsonl_rows,
        create_session,
        flatten_published_file,
        query_files,
        read_json,
        utc_now_iso,
        write_json,
    )
else:
    from .steam_api import (
        API_EXPORT_FIELDS,
        DEFAULT_CURSOR,
        append_csv_rows,
        append_jsonl_rows,
        create_session,
        flatten_published_file,
        query_files,
        read_json,
        utc_now_iso,
        write_json,
    )


LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect all DST mods from Steam QueryFiles with resume support.")
    parser.add_argument("--api-key", required=True, help="Steam Web API key.")
    parser.add_argument("--app-id", type=int, default=322330, help="Consumer app id.")
    parser.add_argument("--num-per-page", type=int, default=100, help="Items per page.")
    parser.add_argument("--sleep-seconds", type=float, default=1.0, help="Delay between requests.")
    parser.add_argument("--batch-id", default=None, help="Optional stable batch id.")
    parser.add_argument("--max-pages", type=int, default=None, help="Optional page cap for smoke tests.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser


def initialize_state(batch_id: str, app_id: int, num_per_page: int) -> dict[str, object]:
    return {
        "batch_id": batch_id,
        "app_id": app_id,
        "num_per_page": num_per_page,
        "completed": False,
        "last_completed_page": 0,
        "next_page": 1,
        "next_cursor": DEFAULT_CURSOR,
        "items_collected": 0,
        "total": None,
        "updated_at_utc": utc_now_iso(),
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    repo_root = Path(__file__).resolve().parents[1]
    batch_id = args.batch_id or utc_now_iso().replace(":", "").replace("-", "").replace("+00:00", "Z")
    crawl_time_utc = utc_now_iso()
    raw_root = repo_root / "data" / "raw" / "steam_api" / batch_id
    raw_pages_root = raw_root / "pages"
    checkpoint_path = raw_root / "checkpoint.json"
    processed_root = repo_root / "data" / "processed" / "steam_api" / batch_id
    csv_path = processed_root / "mods_api_full.csv"
    jsonl_path = processed_root / "mods_api_full.jsonl"
    manifest_path = processed_root / "crawl_manifest.json"

    if checkpoint_path.exists():
        state = read_json(checkpoint_path)
        LOGGER.info("Resuming batch %s from page %s", batch_id, state["next_page"])
        if state.get("completed"):
            LOGGER.info("Batch %s is already marked complete.", batch_id)
            return 0
    else:
        state = initialize_state(batch_id, args.app_id, args.num_per_page)
        write_json(checkpoint_path, state)
        LOGGER.info("Starting new batch %s", batch_id)

    session = create_session()
    pages_processed = 0

    while True:
        current_page = int(state["next_page"])
        current_cursor = state["next_cursor"]
        LOGGER.info("Requesting API page %s with cursor %s", current_page, current_cursor)

        response_payload = query_files(
            session,
            api_key=args.api_key,
            app_id=args.app_id,
            num_per_page=args.num_per_page,
            cursor=str(current_cursor) if current_cursor else DEFAULT_CURSOR,
        )
        response_body = response_payload.get("response", {})
        details = response_body.get("publishedfiledetails", [])
        total = response_body.get("total")
        next_cursor = response_body.get("next_cursor")

        page_raw_path = raw_pages_root / f"page_{current_page:04d}.json"
        write_json(page_raw_path, response_payload)

        rows = [
            flatten_published_file(detail, batch_id=batch_id, crawl_time_utc=crawl_time_utc, api_page=current_page)
            for detail in details
        ]
        append_csv_rows(csv_path, rows, API_EXPORT_FIELDS)
        append_jsonl_rows(jsonl_path, rows)

        state["total"] = total
        state["last_completed_page"] = current_page
        state["next_page"] = current_page + 1
        state["next_cursor"] = next_cursor
        state["items_collected"] = int(state["items_collected"]) + len(rows)
        state["updated_at_utc"] = utc_now_iso()

        no_more_rows = len(rows) == 0
        reached_total = total is not None and int(state["items_collected"]) >= int(total)
        no_more_cursor = not next_cursor or next_cursor == current_cursor
        reached_page_cap = args.max_pages is not None and current_page >= args.max_pages

        state["completed"] = bool(no_more_rows or reached_total or no_more_cursor)
        write_json(checkpoint_path, state)

        pages_processed += 1
        if state["completed"] or reached_page_cap:
            break

        if args.sleep_seconds > 0:
            import time
            time.sleep(args.sleep_seconds)

    write_json(
        manifest_path,
        {
            "batch_id": batch_id,
            "crawl_time_utc": crawl_time_utc,
            "app_id": args.app_id,
            "num_per_page": args.num_per_page,
            "pages_processed_this_run": pages_processed,
            "last_completed_page": state["last_completed_page"],
            "next_page": state["next_page"],
            "next_cursor": state["next_cursor"],
            "items_collected": state["items_collected"],
            "total": state["total"],
            "completed": state["completed"],
            "outputs": {
                "csv": str(csv_path.relative_to(repo_root)),
                "jsonl": str(jsonl_path.relative_to(repo_root)),
                "checkpoint": str(checkpoint_path.relative_to(repo_root)),
            },
            "fields_exported": API_EXPORT_FIELDS,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
