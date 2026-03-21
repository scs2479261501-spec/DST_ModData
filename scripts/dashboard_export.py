from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

if __package__ in {None, ""}:
    from comment_text_analysis import tokenize_text
else:
    from .comment_text_analysis import tokenize_text


AUTHOR_BUCKET_ORDER = ["1", "2-3", "4-9", "10+"]
COMMENT_GROUP_LABELS = {
    "top_100": "Top 100",
    "rank_300_500": "Rank 300-500",
}


def parse_int(value: Any) -> int:
    if value in {None, ""}:
        return 0
    return int(float(value))


def parse_float(value: Any) -> float:
    if value in {None, ""}:
        return 0.0
    return float(value)


def bucket_author_mod_count(mod_count: int) -> str:
    if mod_count <= 1:
        return "1"
    if mod_count <= 3:
        return "2-3"
    if mod_count <= 9:
        return "4-9"
    return "10+"


def enrich_author_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized_rows.append(
            {
                "creator_id": str(row.get("creator_id", "")),
                "mod_count": parse_int(row.get("mod_count")),
                "total_subscriptions": parse_int(row.get("total_subscriptions")),
                "avg_subscriptions": round(parse_float(row.get("avg_subscriptions")), 2),
                "median_subscriptions": round(parse_float(row.get("median_subscriptions")), 2),
                "avg_positive_rate": round(parse_float(row.get("avg_positive_rate")), 6) if row.get("avg_positive_rate") not in {None, ""} else "",
                "avg_maintenance_days": round(parse_float(row.get("avg_maintenance_days")), 2),
                "tag_breadth": parse_int(row.get("tag_breadth")),
            }
        )

    normalized_rows.sort(
        key=lambda row: (
            -int(row["total_subscriptions"]),
            -int(row["mod_count"]),
            str(row["creator_id"]),
        )
    )
    total_subscriptions_all = sum(int(row["total_subscriptions"]) for row in normalized_rows)
    top_1pct_author_count = max(1, math.ceil(len(normalized_rows) * 0.01)) if normalized_rows else 0

    running_total = 0
    enriched_rows: list[dict[str, Any]] = []
    for index, row in enumerate(normalized_rows, start=1):
        running_total += int(row["total_subscriptions"])
        share_pct = (int(row["total_subscriptions"]) / total_subscriptions_all * 100) if total_subscriptions_all else 0.0
        cumulative_share_pct = (running_total / total_subscriptions_all * 100) if total_subscriptions_all else 0.0
        concentration_band = "others"
        if index <= 10:
            concentration_band = "top_10"
        elif index <= top_1pct_author_count:
            concentration_band = "top_1pct_other"

        enriched_row = dict(row)
        enriched_row.update(
            {
                "author_rank": index,
                "productivity_bucket": bucket_author_mod_count(int(row["mod_count"])),
                "share_of_total_subscriptions_pct": round(share_pct, 4),
                "cumulative_subscriptions": running_total,
                "cumulative_share_pct": round(cumulative_share_pct, 4),
                "concentration_band": concentration_band,
            }
        )
        enriched_rows.append(enriched_row)
    return enriched_rows


def build_author_concentration_summary(enriched_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    author_count = len(enriched_rows)
    total_subscriptions_all = sum(int(row["total_subscriptions"]) for row in enriched_rows)
    top_1pct_author_count = max(1, math.ceil(author_count * 0.01)) if author_count else 0
    top_1pct_subscriptions = sum(int(row["total_subscriptions"]) for row in enriched_rows[:top_1pct_author_count])
    top_10_subscriptions = sum(int(row["total_subscriptions"]) for row in enriched_rows[:10])
    return [
        {
            "author_count": author_count,
            "total_subscriptions_all": total_subscriptions_all,
            "top_1pct_author_count": top_1pct_author_count,
            "top_1pct_subscriptions": top_1pct_subscriptions,
            "top_1pct_share_pct": round(top_1pct_subscriptions / total_subscriptions_all * 100, 2) if total_subscriptions_all else 0.0,
            "top_10_subscriptions": top_10_subscriptions,
            "top_10_share_pct": round(top_10_subscriptions / total_subscriptions_all * 100, 2) if total_subscriptions_all else 0.0,
        }
    ]


def build_author_bucket_summary(enriched_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bucket_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in enriched_rows:
        bucket_rows[str(row["productivity_bucket"])].append(row)

    summary_rows: list[dict[str, Any]] = []
    for bucket in AUTHOR_BUCKET_ORDER:
        rows = bucket_rows.get(bucket, [])
        if not rows:
            continue
        summary_rows.append(
            {
                "productivity_bucket": bucket,
                "author_count": len(rows),
                "total_subscriptions": sum(int(row["total_subscriptions"]) for row in rows),
                "avg_total_subscriptions": round(sum(int(row["total_subscriptions"]) for row in rows) / len(rows), 2),
                "avg_avg_subscriptions": round(sum(float(row["avg_subscriptions"]) for row in rows) / len(rows), 2),
                "avg_positive_rate": round(
                    sum(float(row["avg_positive_rate"]) for row in rows if row["avg_positive_rate"] != "") /
                    max(1, sum(1 for row in rows if row["avg_positive_rate"] != "")),
                    6,
                ),
                "avg_maintenance_days": round(sum(float(row["avg_maintenance_days"]) for row in rows) / len(rows), 2),
            }
        )
    return summary_rows


def build_comment_group_summary(
    selected_rows: list[dict[str, Any]],
    comment_rows: list[dict[str, Any]],
    groups: tuple[str, ...] = ("top_100", "rank_300_500"),
) -> list[dict[str, Any]]:
    selected_counts = Counter(str(row.get("rank_group", "")) for row in selected_rows)
    comment_counts = Counter()
    tokenized_comment_counts = Counter()
    mods_with_comments: dict[str, set[str]] = {group: set() for group in groups}

    for row in comment_rows:
        group = str(row.get("rank_group", ""))
        if group not in groups:
            continue
        comment_counts[group] += 1
        mod_id = str(row.get("mod_id", ""))
        if mod_id:
            mods_with_comments[group].add(mod_id)
        if tokenize_text(str(row.get("content_text", "") or "")):
            tokenized_comment_counts[group] += 1

    summary_rows: list[dict[str, Any]] = []
    for group in groups:
        selected_mod_count = selected_counts[group]
        collected_mod_count = len(mods_with_comments[group])
        comment_count = comment_counts[group]
        tokenized_comment_count = tokenized_comment_counts[group]
        summary_rows.append(
            {
                "rank_group": group,
                "group_label": COMMENT_GROUP_LABELS.get(group, group),
                "selected_mod_count": selected_mod_count,
                "mods_with_comments": collected_mod_count,
                "comment_count": comment_count,
                "tokenized_comment_count": tokenized_comment_count,
                "mod_coverage_pct": round(collected_mod_count / selected_mod_count * 100, 2) if selected_mod_count else 0.0,
                "tokenized_comment_share_pct": round(tokenized_comment_count / comment_count * 100, 2) if comment_count else 0.0,
                "avg_comments_per_collected_mod": round(comment_count / collected_mod_count, 2) if collected_mod_count else 0.0,
            }
        )
    return summary_rows
