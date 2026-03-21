from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from dashboard_export import (
        build_author_bucket_summary,
        build_author_concentration_summary,
        build_comment_group_summary,
        enrich_author_rows,
    )
else:
    from .dashboard_export import (
        build_author_bucket_summary,
        build_author_concentration_summary,
        build_comment_group_summary,
        enrich_author_rows,
    )


DATE_TOKEN_RE = re.compile(r"(20\d{6})")
OVERVIEW_KPI_FIELDS = ["metric_key", "metric_label", "metric_value", "display_value", "sort_order"]
COMMENT_TOP_KEYWORD_FIELDS = [
    "token",
    "dominant_group",
    "top_100_comment_count",
    "rank_300_500_comment_count",
    "top_100_comments_per_1000",
    "rank_300_500_comments_per_1000",
    "comments_per_1000_diff",
    "rate_ratio",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export dashboard-ready Power BI datasets.")
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")))
    parser.add_argument("--user", default=os.getenv("MYSQL_USER", "root"))
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD", ""))
    parser.add_argument("--database", default=os.getenv("MYSQL_DATABASE", "steamDST"))
    parser.add_argument("--api-batch-id", default=None, help="Optional explicit API batch id.")
    parser.add_argument("--comment-batch-id", default=None, help="Optional explicit comment batch id.")
    parser.add_argument("--output-batch-id", default=None, help="Optional stable output batch id.")
    return parser


def mysql_connection(args: argparse.Namespace) -> pymysql.Connection:
    return pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        cursorclass=DictCursor,
    )


def clean_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def query_rows(connection: pymysql.Connection, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
    return [{key: clean_value(value) for key, value in row.items()} for row in rows]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def extract_date_token(text: str | None) -> str | None:
    if not text:
        return None
    matches = DATE_TOKEN_RE.findall(text)
    return matches[-1] if matches else None


def find_latest_file(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No files matched {pattern} in {directory}")
    return matches[-1]


def detect_latest_api_batch(connection: pymysql.Connection) -> str:
    query = """
    SELECT batch_id
    FROM steam_api_mods_raw
    GROUP BY batch_id
    ORDER BY MAX(crawl_time_utc) DESC, batch_id DESC
    LIMIT 1;
    """
    rows = query_rows(connection, query)
    if not rows:
        raise ValueError("No API batches found in steam_api_mods_raw.")
    return str(rows[0]["batch_id"])


def detect_comment_batch(analysis_root: Path) -> str:
    latest_file = find_latest_file(analysis_root, "comment_keyword_comparison_*.csv")
    prefix = "comment_keyword_comparison_"
    return latest_file.stem[len(prefix):]


def format_int(value: int) -> str:
    return f"{value:,}"


def build_overview_kpis(connection: pymysql.Connection, api_batch_id: str) -> list[dict[str, Any]]:
    query = """
    SELECT
        COUNT(*) AS mod_count,
        COUNT(DISTINCT creator) AS author_count,
        SUM(subscriptions) AS total_subscriptions
    FROM steam_api_mods_raw
    WHERE batch_id = %s;
    """
    row = query_rows(connection, query, (api_batch_id,))[0]
    mod_count = int(row["mod_count"] or 0)
    author_count = int(row["author_count"] or 0)
    total_subscriptions = int(row["total_subscriptions"] or 0)
    return [
        {
            "metric_key": "mod_count",
            "metric_label": "Mod Count",
            "metric_value": mod_count,
            "display_value": format_int(mod_count),
            "sort_order": 1,
        },
        {
            "metric_key": "author_count",
            "metric_label": "Author Count",
            "metric_value": author_count,
            "display_value": format_int(author_count),
            "sort_order": 2,
        },
        {
            "metric_key": "total_subscriptions",
            "metric_label": "Total Subscriptions",
            "metric_value": total_subscriptions,
            "display_value": format_int(total_subscriptions),
            "sort_order": 3,
        },
    ]


def fetch_tag_dimension(connection: pymysql.Connection, api_batch_id: str) -> list[dict[str, Any]]:
    query = """
    WITH exploded_tags AS (
        SELECT
            s.mod_id,
            LOWER(TRIM(jt.tag)) AS tag,
            s.subscriptions
        FROM steam_api_mods_raw s
        JOIN JSON_TABLE(CAST(s.tags_json AS JSON), '$[*]' COLUMNS(tag VARCHAR(128) PATH '$.tag')) jt
        WHERE s.batch_id = %s
          AND s.tags_json IS NOT NULL
          AND JSON_VALID(s.tags_json) = 1
          AND s.tags_json <> '[]'
          AND jt.tag IS NOT NULL
          AND TRIM(jt.tag) <> ''
          AND LOWER(TRIM(jt.tag)) NOT LIKE 'version:%%'
          AND LOWER(TRIM(jt.tag)) NOT LIKE 'version_compatible:%%'
    )
    SELECT
        tag,
        COUNT(DISTINCT mod_id) AS mod_count,
        ROUND(AVG(subscriptions), 2) AS avg_subscriptions
    FROM exploded_tags
    GROUP BY tag
    ORDER BY mod_count DESC, tag;
    """
    rows = query_rows(connection, query, (api_batch_id,))
    for index, row in enumerate(rows, start=1):
        row["tag_rank_by_mod_count"] = index
        row["wordcloud_weight"] = row["mod_count"]
    return rows


def fetch_activity_mods(connection: pymysql.Connection, api_batch_id: str) -> list[dict[str, Any]]:
    query = """
    WITH base AS (
        SELECT
            mod_id,
            COALESCE(title, '') AS title,
            COALESCE(creator, '') AS creator_id,
            subscriptions,
            votes_up,
            votes_down,
            score,
            time_created_utc,
            time_updated_utc,
            DATEDIFF(time_updated_utc, time_created_utc) AS maintenance_days,
            DATEDIFF(CURDATE(), time_updated_utc) AS days_since_last_update
        FROM steam_api_mods_raw
        WHERE batch_id = %s
          AND subscriptions IS NOT NULL
          AND time_created_utc IS NOT NULL
          AND time_updated_utc IS NOT NULL
    ), ranked_subscriptions AS (
        SELECT
            subscriptions,
            ROW_NUMBER() OVER (ORDER BY subscriptions) AS rn,
            COUNT(*) OVER () AS cnt
        FROM base
    ), ranked_maintenance AS (
        SELECT
            maintenance_days,
            ROW_NUMBER() OVER (ORDER BY maintenance_days) AS rn,
            COUNT(*) OVER () AS cnt
        FROM base
    ), medians AS (
        SELECT
            (SELECT AVG(subscriptions)
             FROM ranked_subscriptions
             WHERE rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2))) AS subscription_median,
            (SELECT AVG(maintenance_days)
             FROM ranked_maintenance
             WHERE rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2))) AS maintenance_median
    )
    SELECT
        b.mod_id,
        b.title,
        b.creator_id,
        b.subscriptions,
        b.votes_up,
        b.votes_down,
        b.score,
        CASE
            WHEN b.votes_up IS NOT NULL AND b.votes_down IS NOT NULL AND (b.votes_up + b.votes_down) > 0
                THEN ROUND(b.votes_up / (b.votes_up + b.votes_down), 6)
            ELSE NULL
        END AS positive_rate,
        b.time_created_utc,
        b.time_updated_utc,
        b.maintenance_days,
        b.days_since_last_update,
        m.subscription_median,
        m.maintenance_median,
        CASE
            WHEN b.subscriptions > m.subscription_median AND b.maintenance_days > m.maintenance_median THEN 'evergreen'
            WHEN b.subscriptions > m.subscription_median AND b.maintenance_days <= m.maintenance_median THEN 'hit_then_abandoned'
            WHEN b.subscriptions <= m.subscription_median AND b.maintenance_days > m.maintenance_median THEN 'passion_project'
            ELSE 'silent_fade'
        END AS quadrant,
        CASE
            WHEN b.subscriptions > m.subscription_median AND b.maintenance_days > m.maintenance_median THEN 'Evergreen'
            WHEN b.subscriptions > m.subscription_median AND b.maintenance_days <= m.maintenance_median THEN 'Hit Then Abandoned'
            WHEN b.subscriptions <= m.subscription_median AND b.maintenance_days > m.maintenance_median THEN 'Passion Project'
            ELSE 'Silent Fade'
        END AS quadrant_label
    FROM base b
    CROSS JOIN medians m
    ORDER BY b.subscriptions DESC, b.mod_id;
    """
    return query_rows(connection, query, (api_batch_id,))


def fetch_activity_mod_tags(connection: pymysql.Connection, api_batch_id: str) -> list[dict[str, Any]]:
    query = """
    WITH base AS (
        SELECT mod_id
        FROM steam_api_mods_raw
        WHERE batch_id = %s
          AND subscriptions IS NOT NULL
          AND time_created_utc IS NOT NULL
          AND time_updated_utc IS NOT NULL
    ), exploded_tags AS (
        SELECT
            s.mod_id,
            LOWER(TRIM(jt.tag)) AS tag
        FROM steam_api_mods_raw s
        JOIN JSON_TABLE(CAST(s.tags_json AS JSON), '$[*]' COLUMNS(tag VARCHAR(128) PATH '$.tag')) jt
        WHERE s.batch_id = %s
          AND s.tags_json IS NOT NULL
          AND JSON_VALID(s.tags_json) = 1
          AND s.tags_json <> '[]'
          AND jt.tag IS NOT NULL
          AND TRIM(jt.tag) <> ''
          AND LOWER(TRIM(jt.tag)) NOT LIKE 'version:%%'
          AND LOWER(TRIM(jt.tag)) NOT LIKE 'version_compatible:%%'
    )
    SELECT DISTINCT
        e.mod_id,
        e.tag
    FROM exploded_tags e
    JOIN base b ON b.mod_id = e.mod_id
    ORDER BY e.mod_id, e.tag;
    """
    return query_rows(connection, query, (api_batch_id, api_batch_id))


def select_top_keywords(comparison_rows: list[dict[str, Any]], limit_per_group: int = 20) -> list[dict[str, Any]]:
    selected_rows: list[dict[str, Any]] = []
    seen = {"top_100": 0, "rank_300_500": 0}
    for row in comparison_rows:
        group = str(row.get("dominant_group", ""))
        if group not in seen:
            continue
        if seen[group] >= limit_per_group:
            continue
        selected_rows.append({field: row.get(field, "") for field in COMMENT_TOP_KEYWORD_FIELDS})
        seen[group] += 1
    return selected_rows


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    analysis_root = repo_root / "data" / "processed" / "analysis"
    workshop_root = repo_root / "data" / "processed" / "steam_workshop"
    dashboard_root = repo_root / "data" / "processed" / "dashboard"

    with mysql_connection(args) as connection:
        api_batch_id = args.api_batch_id or detect_latest_api_batch(connection)
        api_date_token = extract_date_token(api_batch_id) or datetime.now().strftime("%Y%m%d")
        comment_batch_id = args.comment_batch_id or detect_comment_batch(analysis_root)
        output_batch_id = args.output_batch_id or f"powerbi_{api_date_token}"

        tag_supply_path = analysis_root / f"tag_supply_demand_matrix_{api_date_token}.csv"
        if not tag_supply_path.exists():
            tag_supply_path = find_latest_file(analysis_root, "tag_supply_demand_matrix_*.csv")
        author_productivity_path = analysis_root / f"author_productivity_{api_date_token}.csv"
        if not author_productivity_path.exists():
            author_productivity_path = find_latest_file(analysis_root, "author_productivity_*.csv")

        comment_keyword_path = analysis_root / f"comment_keyword_comparison_{comment_batch_id}.csv"
        comment_summary_path = analysis_root / f"comment_group_summary_{comment_batch_id}.csv"
        if not comment_keyword_path.exists():
            raise FileNotFoundError(f"Comment keyword comparison file not found: {comment_keyword_path}")

        selected_mods_path = workshop_root / comment_batch_id / "selected_mods.csv"
        top_comments_path = workshop_root / comment_batch_id / "top_comments.csv"
        if not selected_mods_path.exists() or not top_comments_path.exists():
            raise FileNotFoundError(f"Comment batch inputs not found under {workshop_root / comment_batch_id}")

        output_root = dashboard_root / output_batch_id
        output_root.mkdir(parents=True, exist_ok=True)

        overview_kpis = build_overview_kpis(connection, api_batch_id)
        dim_tags = fetch_tag_dimension(connection, api_batch_id)
        activity_mods = fetch_activity_mods(connection, api_batch_id)
        activity_mod_tags = fetch_activity_mod_tags(connection, api_batch_id)

    supply_demand_rows = load_csv(tag_supply_path)
    author_rows = load_csv(author_productivity_path)
    enriched_authors = enrich_author_rows(author_rows)
    author_concentration_summary = build_author_concentration_summary(enriched_authors)
    author_bucket_summary = build_author_bucket_summary(enriched_authors)
    author_top_20 = enriched_authors[:20]

    selected_mod_rows = load_csv(selected_mods_path)
    top_comment_rows = load_csv(top_comments_path)
    comment_group_summary = build_comment_group_summary(selected_mod_rows, top_comment_rows)
    comment_keyword_rows = load_csv(comment_keyword_path)
    comment_top_keywords = select_top_keywords(comment_keyword_rows, limit_per_group=20)

    write_csv(output_root / "overview_kpis.csv", overview_kpis, OVERVIEW_KPI_FIELDS)
    write_csv(output_root / "dim_tags.csv", dim_tags)
    write_csv(output_root / "activity_mods.csv", activity_mods)
    write_csv(output_root / "activity_mod_tags.csv", activity_mod_tags)
    write_csv(output_root / "supply_demand_tags.csv", supply_demand_rows)
    write_csv(output_root / "comments_group_summary.csv", comment_group_summary)
    write_csv(output_root / "comments_keyword_comparison.csv", comment_keyword_rows)
    write_csv(output_root / "comments_top_keywords.csv", comment_top_keywords, COMMENT_TOP_KEYWORD_FIELDS)
    write_csv(output_root / "authors_productivity.csv", enriched_authors)
    write_csv(output_root / "authors_concentration_summary.csv", author_concentration_summary)
    write_csv(output_root / "authors_concentration_curve.csv", enriched_authors)
    write_csv(output_root / "authors_bucket_summary.csv", author_bucket_summary)
    write_csv(output_root / "authors_top_20.csv", author_top_20)

    manifest = {
        "output_batch_id": output_batch_id,
        "created_at": datetime.now().isoformat(),
        "source_api_batch_id": api_batch_id,
        "source_comment_batch_id": comment_batch_id,
        "source_files": {
            "tag_supply_demand": str(tag_supply_path.relative_to(repo_root)),
            "author_productivity": str(author_productivity_path.relative_to(repo_root)),
            "comment_keyword_comparison": str(comment_keyword_path.relative_to(repo_root)),
            "comment_group_summary": str(comment_summary_path.relative_to(repo_root)) if comment_summary_path.exists() else "",
            "selected_mods": str(selected_mods_path.relative_to(repo_root)),
            "top_comments": str(top_comments_path.relative_to(repo_root)),
        },
        "outputs": sorted(str(path.relative_to(repo_root)) for path in output_root.glob("*.csv")),
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
