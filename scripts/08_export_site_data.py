#!/usr/bin/env python3
"""
08_export_site_data.py — Convert dashboard CSVs to the compact JSON format
expected by the React site (site/public/data/*.json).

The site uses a columnar {meta, fields, items} format where each item is an
array of values (not an object), keyed by short field names defined in `fields`.

Usage:
    python scripts/08_export_site_data.py --dashboard-batch powerbi_20260323b
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
from collections import defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_ROOT = REPO_ROOT / "data" / "processed" / "dashboard"
SITE_DATA_DIR = REPO_ROOT / "site" / "public" / "data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_site_json(name: str, data: dict) -> None:
    out = SITE_DATA_DIR / f"{name}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    logger.info("  Wrote %s (%d items)", out.name, len(data.get("items", [])))


def to_int(v, default=0):
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


def to_float(v, default=0.0):
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Exporters
# ---------------------------------------------------------------------------

def extract_batch_date(batch_name: str) -> str:
    """Extract date from batch folder name like 'powerbi_20260323b' → '2026-03-23'."""
    m = re.search(r"(\d{4})(\d{2})(\d{2})", batch_name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return batch_name


def export_overview_kpis(db: Path) -> None:
    rows = read_csv(db / "overview_kpis.csv")
    # The site also expects subscription_median and maintenance_median KPIs.
    # If missing from dashboard, compute from activity_mods.
    existing_keys = {r["metric_key"] for r in rows}
    need_medians = "subscription_median" not in existing_keys or "maintenance_median" not in existing_keys

    if need_medians and (db / "activity_mods.csv").exists():
        mods = read_csv(db / "activity_mods.csv")
        subs = sorted([to_int(m["subscriptions"]) for m in mods])
        maint = sorted([to_float(m["maintenance_days"]) for m in mods])
        mid = len(subs) // 2
        sub_med = subs[mid] if subs else 0
        maint_med = maint[mid] if maint else 0

        if "subscription_median" not in existing_keys:
            rows.append({
                "metric_key": "subscription_median",
                "metric_label": "Subscription Median",
                "metric_value": str(sub_med),
                "display_value": f"{sub_med:,}",
                "sort_order": "4",
            })
        if "maintenance_median" not in existing_keys:
            rows.append({
                "metric_key": "maintenance_median",
                "metric_label": "Maintenance Median (days)",
                "metric_value": str(maint_med),
                "display_value": f"{maint_med:g}",
                "sort_order": "5",
            })

    rows.sort(key=lambda r: to_int(r.get("sort_order", "99")))
    items = []
    for r in rows:
        items.append({
            "key": r["metric_key"],
            "label": r["metric_label"],
            "value": to_float(r["metric_value"]) if "." in r["metric_value"] else to_int(r["metric_value"]),
            "display": r["display_value"],
            "sort": to_int(r.get("sort_order", 99)),
        })

    batch_date = extract_batch_date(db.name)
    write_site_json("overview_kpis", {
        "meta": {"rowCount": len(items), "batchDate": batch_date, "description": "首页概览 KPI 数据。"},
        "items": items,
    })


def export_mods(db: Path) -> None:
    mods_rows = read_csv(db / "activity_mods.csv")
    tags_rows = read_csv(db / "activity_mod_tags.csv")

    # Build mod_id → [tag, ...] mapping
    mod_tags: dict[str, list[str]] = defaultdict(list)
    for tr in tags_rows:
        mod_tags[tr["mod_id"]].append(tr["tag"])

    # Sort by subscriptions desc for ranking
    mods_rows.sort(key=lambda r: to_int(r["subscriptions"]), reverse=True)

    # Get medians for quadrant reference lines
    subs_list = sorted([to_int(m["subscriptions"]) for m in mods_rows])
    sub_median = subs_list[len(subs_list) // 2] if subs_list else 232
    maint_list = sorted([to_float(m["maintenance_days"]) for m in mods_rows])
    maint_median = maint_list[len(maint_list) // 2] if maint_list else 1

    fields = ["id", "t", "k", "cid", "s", "up", "down", "sc", "pr",
              "ct", "ut", "md", "du", "sm", "mm", "q", "ql", "tg", "rk"]
    items = []
    for rank, m in enumerate(mods_rows, 1):
        items.append([
            m["mod_id"],
            m["title"],
            m["title"].lower(),  # searchKey
            m["creator_id"],
            to_int(m["subscriptions"]),
            to_int(m["votes_up"]),
            to_int(m["votes_down"]),
            to_float(m["score"]),
            to_float(m["positive_rate"]),
            m["time_created_utc"],
            m["time_updated_utc"],
            to_int(m["maintenance_days"]),
            to_int(m["days_since_last_update"]),
            float(sub_median),
            float(maint_median),
            m["quadrant"],
            m["quadrant_label"],
            mod_tags.get(m["mod_id"], []),
            rank,
        ])

    write_site_json("mods", {
        "meta": {"rowCount": len(items), "description": "Mod 主表数据。"},
        "fields": fields,
        "items": items,
    })


def export_authors(db: Path) -> None:
    authors_rows = read_csv(db / "authors_productivity.csv")
    mods_rows = read_csv(db / "activity_mods.csv")

    # Build creator_id → [mod_id, ...] sorted by subscriptions desc
    creator_mods: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for m in mods_rows:
        creator_mods[m["creator_id"]].append((to_int(m["subscriptions"]), m["mod_id"]))
    for k in creator_mods:
        creator_mods[k].sort(reverse=True)

    # Sort by total_subscriptions desc for ranking
    authors_rows.sort(key=lambda r: to_float(r["total_subscriptions"]), reverse=True)

    fields = ["id", "mc", "ts", "as", "ms", "pr", "amd", "tb",
              "rk", "pb", "sp", "cp", "cb", "mods"]
    items = []
    for rank, a in enumerate(authors_rows, 1):
        cid = a["creator_id"]
        mod_ids = [mid for _, mid in creator_mods.get(cid, [])]
        items.append([
            cid,
            to_int(a["mod_count"]),
            to_float(a["total_subscriptions"]),
            to_float(a["avg_subscriptions"]),
            to_float(a["median_subscriptions"]),
            to_float(a["avg_positive_rate"]),
            to_float(a["avg_maintenance_days"]),
            to_int(a["tag_breadth"]),
            rank,
            a["productivity_bucket"],
            to_float(a["share_of_total_subscriptions_pct"]),
            to_float(a["cumulative_share_pct"]),
            a["concentration_band"],
            mod_ids,
        ])

    write_site_json("authors", {
        "meta": {"rowCount": len(items), "description": "作者聚合表数据。"},
        "fields": fields,
        "items": items,
    })


def export_dim_tags(db: Path) -> None:
    rows = read_csv(db / "dim_tags.csv")
    rows.sort(key=lambda r: to_int(r["mod_count"]), reverse=True)

    fields = ["tag", "mc", "avg", "rk", "w"]
    items = []
    for r in rows:
        items.append([
            r["tag"],
            to_int(r["mod_count"]),
            to_float(r["avg_subscriptions"]),
            to_int(r["tag_rank_by_mod_count"]),
            to_int(r["wordcloud_weight"]),
        ])

    write_site_json("dim_tags", {
        "meta": {"rowCount": len(items), "description": "标签维表数据。"},
        "fields": fields,
        "items": items,
    })


def export_supply_demand(db: Path) -> None:
    rows = read_csv(db / "supply_demand_tags.csv")
    rows.sort(key=lambda r: to_float(r["median_subscriptions"]), reverse=True)

    fields = ["tag", "mc", "avg", "med", "p75", "stable", "st", "dt", "pt", "ss", "ds", "zone"]
    items = []
    for r in rows:
        items.append([
            r["tag"],
            to_int(r["mod_count"]),
            to_float(r["avg_subscriptions"]),
            to_float(r["median_subscriptions"]),
            to_float(r["p75_subscriptions"]),
            to_int(r["is_stable_tag"]),
            to_int(r["supply_median_threshold"]),
            to_float(r["demand_median_threshold"]),
            to_float(r["p75_median_threshold"]),
            r["supply_side"],
            r["demand_side"],
            r["market_zone"],
        ])

    write_site_json("tags_supply_demand", {
        "meta": {"rowCount": len(items), "description": "标签供需矩阵数据。"},
        "fields": fields,
        "items": items,
    })


def export_comments(db: Path) -> None:
    kw_rows = read_csv(db / "comments_keyword_comparison.csv")
    grp_rows = read_csv(db / "comments_group_summary.csv")

    # Build groups meta
    groups = []
    for g in grp_rows:
        groups.append({
            "group": g["rank_group"],
            "label": g["group_label"],
            "selected": to_int(g["selected_mod_count"]),
            "modsWithComments": to_int(g["mods_with_comments"]),
            "comments": to_int(g["comment_count"]),
            "tokenized": to_int(g["tokenized_comment_count"]),
            "coverage": to_float(g["mod_coverage_pct"]),
        })

    fields = ["t", "g", "c1", "c2", "p1", "p2", "d", "rr"]
    items = []
    for r in kw_rows:
        rr = to_float(r.get("rate_ratio", "")) if r.get("rate_ratio", "") else None
        items.append([
            r["token"],
            r["dominant_group"],
            to_int(r["top_100_comment_count"]),
            to_int(r["rank_300_500_comment_count"]),
            to_float(r["top_100_comments_per_1000"]),
            to_float(r["rank_300_500_comments_per_1000"]),
            to_float(r["comments_per_1000_diff"]),
            rr,
        ])

    write_site_json("comments_keywords", {
        "meta": {
            "rowCount": len(items),
            "groups": groups,
            "description": "评论关键词差异数据。",
        },
        "fields": fields,
        "items": items,
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Export site JSON from dashboard CSVs")
    parser.add_argument("--dashboard-batch", required=True, help="Dashboard batch folder name")
    args = parser.parse_args()

    db = DASHBOARD_ROOT / args.dashboard_batch
    if not db.exists():
        raise FileNotFoundError(f"Dashboard batch not found: {db}")

    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Exporting site data from %s → %s", db, SITE_DATA_DIR)

    export_overview_kpis(db)
    export_mods(db)
    export_authors(db)
    export_dim_tags(db)
    export_supply_demand(db)
    export_comments(db)

    logger.info("Site data export complete.")


if __name__ == "__main__":
    main()
