from __future__ import annotations

import csv
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


WORKSHOP_APP_ID = 322330
BROWSE_URL = "https://steamcommunity.com/workshop/browse/"
DETAIL_URL = "https://steamcommunity.com/sharedfiles/filedetails/"
COMMENTS_URL = "https://steamcommunity.com/sharedfiles/filedetails/comments/"
DEFAULT_TIMEOUT = 30

DEFAULT_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
}

BROWSE_PAGE_INFO_RE = re.compile(
    r"Showing\s+(?P<range_start>[\d,]+)-(?P<range_end>[\d,]+)\s+of\s+(?P<total_entries>[\d,]+)\s+entries"
)
COMMENT_ID_RE = re.compile(r"comment_(\d+)")
DETAIL_OWNER_RE = re.compile(r'"owner":"(\d+)"')
PROFILE_ID_RE = re.compile(r"/profiles/(\d+)")
SIZE_RE = re.compile(r"(?P<value>[\d.]+)\s*(?P<unit>[KMGTP]?B)", re.IGNORECASE)

LOGGER = logging.getLogger(__name__)

MOD_EXPORT_FIELDS = [
    "batch_id",
    "crawl_time_utc",
    "source_method",
    "discover_page",
    "discover_rank",
    "mod_id",
    "title",
    "detail_url",
    "preview_image_url",
    "owner_steam_id",
    "creator_display_names",
    "creator_profile_urls",
    "creator_miniprofile_ids",
    "tags",
    "description_text",
    "description_length",
    "unique_visitors",
    "current_subscribers",
    "current_favorites",
    "ratings_count",
    "file_size_text",
    "file_size_bytes",
    "posted_text",
    "updated_text",
    "posted_at_naive",
    "updated_at_naive",
    "raw_detail_path",
]

COMMENT_EXPORT_FIELDS = [
    "batch_id",
    "crawl_time_utc",
    "mod_id",
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


def create_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_text(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    response = session.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.text


def sleep_if_needed(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_int(value: str | None) -> int | None:
    if not value:
        return None
    digits_only = re.sub(r"[^\d]", "", value)
    return int(digits_only) if digits_only else None


def parse_display_datetime(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = " ".join(value.split())
    for fmt in ("%d %b, %Y @ %I:%M%p", "%d %b %Y @ %I:%M%p"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    return None


def parse_size_to_bytes(value: str | None) -> int | None:
    if not value:
        return None
    match = SIZE_RE.search(value)
    if not match:
        return None
    amount = float(match.group("value"))
    unit = match.group("unit").upper()
    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    return int(amount * multipliers[unit]) if unit in multipliers else None


def normalize_multiline_text(value: str | None) -> str | None:
    if value is None:
        return None
    lines = [line.strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_mod_id_from_url(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    mod_ids = query.get("id")
    if not mod_ids or not mod_ids[0]:
        raise ValueError(f"Could not extract mod id from URL: {url}")
    return mod_ids[0]


def extract_profile_steam_id(profile_url: str | None) -> str | None:
    if not profile_url:
        return None
    match = PROFILE_ID_RE.search(profile_url)
    return match.group(1) if match else None


def extract_owner_steam_id(html: str) -> str | None:
    match = DETAIL_OWNER_RE.search(html)
    return match.group(1) if match else None


def parse_workshop_browse_page(html: str, *, source_url: str, page_number: int) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    page_info_node = soup.select_one(".workshopBrowsePagingInfo")
    if page_info_node is None:
        raise ValueError("Could not find browse page paging info.")
    page_info_text = page_info_node.get_text(" ", strip=True)
    page_info_match = BROWSE_PAGE_INFO_RE.search(page_info_text)
    if page_info_match is None:
        raise ValueError(f"Could not parse browse page info from: {page_info_text}")

    items: list[dict[str, Any]] = []
    for item_rank, item_node in enumerate(soup.select(".workshopItem"), start=1):
        ugc_link = item_node.select_one("a.ugc[data-publishedfileid]")
        title_node = item_node.select_one(".workshopItemTitle")
        preview_node = item_node.select_one("img.workshopItemPreviewImage")
        if ugc_link is None or title_node is None:
            raise ValueError("Workshop browse card is missing a required selector.")
        detail_url = ugc_link.get("href")
        mod_id = ugc_link.get("data-publishedfileid")
        if not detail_url or not mod_id:
            raise ValueError("Workshop browse card is missing a detail URL or published file id.")
        items.append(
            {
                "discover_page": page_number,
                "discover_page_rank": item_rank,
                "mod_id": mod_id,
                "title": title_node.get_text(" ", strip=True),
                "detail_url": detail_url,
                "preview_image_url": preview_node.get("src") if preview_node else None,
            }
        )

    return {
        "source_url": source_url,
        "page_number": page_number,
        "range_start": parse_int(page_info_match.group("range_start")),
        "range_end": parse_int(page_info_match.group("range_end")),
        "total_entries": parse_int(page_info_match.group("total_entries")),
        "items": items,
    }


def parse_creator_blocks(soup: BeautifulSoup) -> list[dict[str, Any]]:
    creators: list[dict[str, Any]] = []
    for creator_node in soup.select(".creatorsBlock .friendBlock"):
        content_node = creator_node.select_one(".friendBlockContent")
        overlay_node = creator_node.select_one(".friendBlockLinkOverlay")
        content_text = content_node.get_text("\n", strip=True) if content_node else ""
        creators.append(
            {
                "display_name": content_text.splitlines()[0] if content_text else None,
                "profile_url": overlay_node.get("href") if overlay_node else None,
                "miniprofile_id": creator_node.get("data-miniprofile"),
            }
        )
    return creators


def parse_detail_stat_blocks(soup: BeautifulSoup) -> dict[str, str]:
    left_nodes = soup.select(".detailsStatsContainerLeft .detailsStatLeft")
    right_nodes = soup.select(".detailsStatsContainerRight .detailsStatRight")
    if not left_nodes or not right_nodes or len(left_nodes) != len(right_nodes):
        raise ValueError("Could not match detail stat labels to values.")
    return {
        left_node.get_text(" ", strip=True): right_node.get_text(" ", strip=True)
        for left_node, right_node in zip(left_nodes, right_nodes)
    }


def parse_traffic_stats(soup: BeautifulSoup) -> dict[str, int | None]:
    stats: dict[str, int | None] = {}
    stats_table = soup.select_one(".stats_table")
    if stats_table is None:
        return stats
    for row in stats_table.select("tr"):
        cells = row.select("td")
        if len(cells) != 2:
            continue
        value = parse_int(cells[0].get_text(" ", strip=True))
        label = cells[1].get_text(" ", strip=True)
        stats[label] = value
    return stats


def parse_workshop_detail_page(html: str, *, source_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one(".workshopItemTitle")
    if title_node is None:
        raise ValueError("Could not find the workshop item title on the detail page.")

    detail_stats = parse_detail_stat_blocks(soup)
    traffic_stats = parse_traffic_stats(soup)
    creators = parse_creator_blocks(soup)
    description_node = soup.select_one(".workshopItemDescription")
    og_image_node = soup.select_one("meta[property='og:image']")
    ratings_node = soup.select_one(".numRatings")

    tags = [
        tag_node.get_text(" ", strip=True)
        for tag_node in soup.select(".workshopTags a")
        if tag_node.get_text(" ", strip=True)
    ]
    description_text = normalize_multiline_text(
        description_node.get_text("\n", strip=True) if description_node else None
    )

    creator_display_names = [creator["display_name"] for creator in creators if creator["display_name"]]
    creator_profile_urls = [creator["profile_url"] for creator in creators if creator["profile_url"]]
    creator_miniprofile_ids = [creator["miniprofile_id"] for creator in creators if creator["miniprofile_id"]]

    return {
        "mod_id": extract_mod_id_from_url(source_url),
        "title": title_node.get_text(" ", strip=True),
        "detail_url": source_url,
        "preview_image_url": og_image_node.get("content") if og_image_node else None,
        "owner_steam_id": extract_owner_steam_id(html),
        "creator_display_names": creator_display_names,
        "creator_profile_urls": creator_profile_urls,
        "creator_miniprofile_ids": creator_miniprofile_ids,
        "tags": tags,
        "description_text": description_text,
        "description_length": len(description_text) if description_text else 0,
        "unique_visitors": traffic_stats.get("Unique Visitors"),
        "current_subscribers": traffic_stats.get("Current Subscribers"),
        "current_favorites": traffic_stats.get("Current Favorites"),
        "ratings_count": parse_int(ratings_node.get_text(" ", strip=True) if ratings_node else None),
        "file_size_text": detail_stats.get("File Size"),
        "file_size_bytes": parse_size_to_bytes(detail_stats.get("File Size")),
        "posted_text": detail_stats.get("Posted"),
        "updated_text": detail_stats.get("Updated"),
        "posted_at_naive": parse_display_datetime(detail_stats.get("Posted")),
        "updated_at_naive": parse_display_datetime(detail_stats.get("Updated")),
    }


def parse_workshop_comments_page(html: str, *, mod_id: str, comment_page: int) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    comments: list[dict[str, Any]] = []
    for comment_node in soup.select(".commentthread_comment"):
        raw_comment_id = comment_node.get("id")
        if not raw_comment_id:
            continue
        comment_id_match = COMMENT_ID_RE.search(raw_comment_id)
        if comment_id_match is None:
            continue

        author_link = comment_node.select_one(".commentthread_author_link")
        timestamp_node = comment_node.select_one(".commentthread_comment_timestamp")
        content_node = comment_node.select_one(".commentthread_comment_text")

        profile_url = author_link.get("href") if author_link else None
        timestamp_epoch_text = timestamp_node.get("data-timestamp") if timestamp_node else None
        timestamp_epoch = int(timestamp_epoch_text) if timestamp_epoch_text else None
        timestamp_utc = (
            datetime.fromtimestamp(timestamp_epoch, tz=timezone.utc).replace(microsecond=0).isoformat()
            if timestamp_epoch is not None
            else None
        )

        comments.append(
            {
                "mod_id": mod_id,
                "comment_page": comment_page,
                "comment_id": comment_id_match.group(1),
                "commenter_name": author_link.get_text(" ", strip=True) if author_link else None,
                "commenter_profile_url": profile_url,
                "commenter_steam_id": extract_profile_steam_id(profile_url),
                "commenter_miniprofile_id": author_link.get("data-miniprofile") if author_link else None,
                "comment_timestamp_epoch": timestamp_epoch,
                "comment_timestamp_utc": timestamp_utc,
                "comment_timestamp_text": timestamp_node.get_text(" ", strip=True) if timestamp_node else None,
                "content_text": normalize_multiline_text(
                    content_node.get_text("\n", strip=True) if content_node else None
                ),
                "content_html": content_node.decode_contents().strip() if content_node else None,
            }
        )
    return comments


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _serialize_export_row(row: dict[str, Any], fieldnames: list[str]) -> dict[str, Any]:
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


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(_serialize_export_row(row, fieldnames))


def write_jsonl_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8") as jsonl_file:
        for row in rows:
            jsonl_file.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_discovery_and_detail(
    discover_item: dict[str, Any],
    detail_item: dict[str, Any],
    *,
    batch_id: str,
    crawl_time_utc: str,
    raw_detail_path: str,
) -> dict[str, Any]:
    return {
        "batch_id": batch_id,
        "crawl_time_utc": crawl_time_utc,
        "source_method": "public_workshop_html",
        "discover_page": discover_item["discover_page"],
        "discover_rank": discover_item["discover_page_rank"],
        "mod_id": detail_item["mod_id"],
        "title": detail_item["title"] or discover_item["title"],
        "detail_url": detail_item["detail_url"],
        "preview_image_url": detail_item["preview_image_url"] or discover_item.get("preview_image_url"),
        "owner_steam_id": detail_item["owner_steam_id"],
        "creator_display_names": detail_item["creator_display_names"],
        "creator_profile_urls": detail_item["creator_profile_urls"],
        "creator_miniprofile_ids": detail_item["creator_miniprofile_ids"],
        "tags": detail_item["tags"],
        "description_text": detail_item["description_text"],
        "description_length": detail_item["description_length"],
        "unique_visitors": detail_item["unique_visitors"],
        "current_subscribers": detail_item["current_subscribers"],
        "current_favorites": detail_item["current_favorites"],
        "ratings_count": detail_item["ratings_count"],
        "file_size_text": detail_item["file_size_text"],
        "file_size_bytes": detail_item["file_size_bytes"],
        "posted_text": detail_item["posted_text"],
        "updated_text": detail_item["updated_text"],
        "posted_at_naive": detail_item["posted_at_naive"],
        "updated_at_naive": detail_item["updated_at_naive"],
        "raw_detail_path": raw_detail_path,
    }


def attach_comment_metadata(
    comment: dict[str, Any],
    *,
    batch_id: str,
    crawl_time_utc: str,
    raw_comments_path: str,
) -> dict[str, Any]:
    enriched = dict(comment)
    enriched["batch_id"] = batch_id
    enriched["crawl_time_utc"] = crawl_time_utc
    enriched["raw_comments_path"] = raw_comments_path
    return enriched


def log_summary(mods: list[dict[str, Any]], comments: list[dict[str, Any]]) -> None:
    LOGGER.info("Collected %s mod detail rows.", len(mods))
    LOGGER.info("Collected %s comment rows.", len(comments))
