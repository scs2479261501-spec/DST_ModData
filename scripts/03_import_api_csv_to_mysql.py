from __future__ import annotations

import argparse
import csv
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pymysql


LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load a Steam API CSV export into MySQL.")
    parser.add_argument("--csv-path", required=True, help="Path to the API CSV export.")
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "127.0.0.1"), help="MySQL host.")
    parser.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")), help="MySQL port.")
    parser.add_argument("--user", default=os.getenv("MYSQL_USER"), help="MySQL user.")
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD"), help="MySQL password.")
    parser.add_argument("--database", default=os.getenv("MYSQL_DATABASE"), help="MySQL database name.")
    parser.add_argument("--table", default="steam_api_mods_raw", help="Destination table name.")
    parser.add_argument("--chunk-size", type=int, default=500, help="Rows per executemany batch.")
    parser.add_argument("--dry-run", action="store_true", help="Parse the CSV and print counts without connecting.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser


def to_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def to_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def iso_to_mysql_datetime(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def row_to_tuple(row: dict[str, str]) -> tuple:
    return (
        row.get("batch_id") or None,
        to_int(row.get("publishedfileid")),
        to_int(row.get("api_page")),
        row.get("title") or None,
        to_int(row.get("creator")),
        to_int(row.get("consumer_appid")),
        to_int(row.get("time_created")),
        iso_to_mysql_datetime(row.get("time_created_utc")),
        to_int(row.get("time_updated")),
        iso_to_mysql_datetime(row.get("time_updated_utc")),
        to_int(row.get("subscriptions")),
        to_int(row.get("favorited")),
        to_int(row.get("lifetime_subscriptions")),
        to_int(row.get("lifetime_favorited")),
        to_int(row.get("views")),
        to_int(row.get("num_comments_public")),
        to_int(row.get("votes_up")),
        to_int(row.get("votes_down")),
        to_float(row.get("score")),
        to_int(row.get("file_size")),
        row.get("preview_url") or None,
        row.get("file_url") or None,
        row.get("short_description") or None,
        row.get("tags_json") or None,
        iso_to_mysql_datetime(row.get("crawl_time_utc")),
    )


def iter_csv_rows(csv_path: Path) -> Iterable[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            yield row


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        parser.error(f"CSV file not found: {csv_path}")

    rows = [row_to_tuple(row) for row in iter_csv_rows(csv_path)]
    LOGGER.info("Parsed %s rows from %s", len(rows), csv_path)

    if args.dry_run:
        LOGGER.info("Dry run only. No database connection attempted.")
        if rows:
            LOGGER.info("First mod id: %s", rows[0][1])
        return 0

    if not args.user or not args.database:
        parser.error("--user and --database are required unless --dry-run is used.")

    connection = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        autocommit=False,
    )

    insert_sql = f"""
        INSERT INTO {args.table} (
            batch_id,
            mod_id,
            api_page,
            title,
            creator,
            consumer_appid,
            time_created_epoch,
            time_created_utc,
            time_updated_epoch,
            time_updated_utc,
            subscriptions,
            favorited,
            lifetime_subscriptions,
            lifetime_favorited,
            views,
            num_comments_public,
            votes_up,
            votes_down,
            score,
            file_size,
            preview_url,
            file_url,
            short_description,
            tags_json,
            crawl_time_utc
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            api_page = VALUES(api_page),
            title = VALUES(title),
            creator = VALUES(creator),
            consumer_appid = VALUES(consumer_appid),
            time_created_epoch = VALUES(time_created_epoch),
            time_created_utc = VALUES(time_created_utc),
            time_updated_epoch = VALUES(time_updated_epoch),
            time_updated_utc = VALUES(time_updated_utc),
            subscriptions = VALUES(subscriptions),
            favorited = VALUES(favorited),
            lifetime_subscriptions = VALUES(lifetime_subscriptions),
            lifetime_favorited = VALUES(lifetime_favorited),
            views = VALUES(views),
            num_comments_public = VALUES(num_comments_public),
            votes_up = VALUES(votes_up),
            votes_down = VALUES(votes_down),
            score = VALUES(score),
            file_size = VALUES(file_size),
            preview_url = VALUES(preview_url),
            file_url = VALUES(file_url),
            short_description = VALUES(short_description),
            tags_json = VALUES(tags_json),
            crawl_time_utc = VALUES(crawl_time_utc)
    """

    inserted = 0
    try:
        with connection.cursor() as cursor:
            for start in range(0, len(rows), args.chunk_size):
                chunk = rows[start : start + args.chunk_size]
                cursor.executemany(insert_sql, chunk)
                connection.commit()
                inserted += len(chunk)
                LOGGER.info("Loaded %s/%s rows into %s", inserted, len(rows), args.table)
    finally:
        connection.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
