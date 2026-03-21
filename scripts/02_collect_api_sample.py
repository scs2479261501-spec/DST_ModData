from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from steam_api import (
        API_EXPORT_FIELDS,
        create_session,
        flatten_published_file,
        query_files,
        utc_now_iso,
        write_csv,
        write_json,
    )
else:
    from .steam_api import (
        API_EXPORT_FIELDS,
        create_session,
        flatten_published_file,
        query_files,
        utc_now_iso,
        write_csv,
        write_json,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pull a small DST sample from Steam QueryFiles API.")
    parser.add_argument("--api-key", required=True, help="Steam Web API key.")
    parser.add_argument("--page", type=int, default=1, help="API page number.")
    parser.add_argument("--num-per-page", type=int, default=10, help="Number of items to request.")
    parser.add_argument("--app-id", type=int, default=322330, help="Consumer app id.")
    parser.add_argument("--batch-id", default=None, help="Optional stable batch id.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    batch_id = args.batch_id or utc_now_iso().replace(":", "").replace("-", "").replace("+00:00", "Z")
    crawl_time_utc = utc_now_iso()
    raw_root = repo_root / "data" / "raw" / "steam_api" / batch_id
    processed_root = repo_root / "data" / "processed" / "steam_api" / batch_id

    session = create_session()
    response_payload = query_files(
        session,
        api_key=args.api_key,
        app_id=args.app_id,
        page=args.page,
        num_per_page=args.num_per_page,
    )
    details = response_payload.get("response", {}).get("publishedfiledetails", [])
    rows = [
        flatten_published_file(detail, batch_id=batch_id, crawl_time_utc=crawl_time_utc, api_page=args.page)
        for detail in details
    ]

    write_json(raw_root / "queryfiles_response.json", response_payload)
    write_csv(processed_root / "mods_api_sample.csv", rows, API_EXPORT_FIELDS)
    write_json(
        processed_root / "crawl_manifest.json",
        {
            "batch_id": batch_id,
            "crawl_time_utc": crawl_time_utc,
            "app_id": args.app_id,
            "page": args.page,
            "num_per_page": args.num_per_page,
            "items_returned": len(rows),
            "fields_exported": API_EXPORT_FIELDS,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
