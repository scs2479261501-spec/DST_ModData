from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from steam_workshop import create_session, ensure_directory
else:
    from .steam_workshop import create_session, ensure_directory


QUERY_FILES_URL = "https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/"
DEFAULT_APP_ID = 322330
DEFAULT_CURSOR = "*"

API_EXPORT_FIELDS = [
    "batch_id",
    "crawl_time_utc",
    "api_page",
    "publishedfileid",
    "title",
    "creator",
    "consumer_appid",
    "time_created",
    "time_created_utc",
    "time_updated",
    "time_updated_utc",
    "subscriptions",
    "favorited",
    "lifetime_subscriptions",
    "lifetime_favorited",
    "views",
    "num_comments_public",
    "votes_up",
    "votes_down",
    "score",
    "file_size",
    "preview_url",
    "file_url",
    "short_description",
    "tags_json",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def epoch_to_utc_iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc).replace(microsecond=0).isoformat()


def query_files(
    session: requests.Session,
    *,
    api_key: str,
    app_id: int = DEFAULT_APP_ID,
    num_per_page: int = 10,
    page: int | None = None,
    cursor: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "key": api_key,
        "appid": app_id,
        "numperpage": num_per_page,
        "return_vote_data": "true",
        "return_tags": "true",
        "return_previews": "true",
        "return_metadata": "true",
        "return_short_description": "true",
    }
    if cursor is not None:
        params["cursor"] = cursor
    elif page is not None:
        params["page"] = page
    else:
        params["page"] = 1

    response = session.get(QUERY_FILES_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def flatten_published_file(
    detail: dict[str, Any],
    *,
    batch_id: str,
    crawl_time_utc: str,
    api_page: int | None = None,
) -> dict[str, Any]:
    vote_data = detail.get("vote_data") or {}
    return {
        "batch_id": batch_id,
        "crawl_time_utc": crawl_time_utc,
        "api_page": api_page,
        "publishedfileid": detail.get("publishedfileid"),
        "title": detail.get("title"),
        "creator": detail.get("creator"),
        "consumer_appid": detail.get("consumer_appid"),
        "time_created": detail.get("time_created"),
        "time_created_utc": epoch_to_utc_iso(detail.get("time_created")),
        "time_updated": detail.get("time_updated"),
        "time_updated_utc": epoch_to_utc_iso(detail.get("time_updated")),
        "subscriptions": detail.get("subscriptions"),
        "favorited": detail.get("favorited"),
        "lifetime_subscriptions": detail.get("lifetime_subscriptions"),
        "lifetime_favorited": detail.get("lifetime_favorited"),
        "views": detail.get("views"),
        "num_comments_public": detail.get("num_comments_public"),
        "votes_up": vote_data.get("votes_up"),
        "votes_down": vote_data.get("votes_down"),
        "score": vote_data.get("score"),
        "file_size": detail.get("file_size"),
        "preview_url": detail.get("preview_url"),
        "file_url": detail.get("file_url"),
        "short_description": detail.get("short_description"),
        "tags_json": json.dumps(detail.get("tags", []), ensure_ascii=False),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    ensure_directory(path.parent)
    effective_fieldnames = fieldnames or API_EXPORT_FIELDS
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=effective_fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def append_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if not rows:
        return
    ensure_directory(path.parent)
    effective_fieldnames = fieldnames or API_EXPORT_FIELDS
    file_exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=effective_fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def append_jsonl_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    ensure_directory(path.parent)
    with path.open("a", encoding="utf-8") as jsonl_file:
        for row in rows:
            jsonl_file.write(json.dumps(row, ensure_ascii=False) + "\n")
