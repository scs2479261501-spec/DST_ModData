from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable


ENGLISH_TOKEN_RE = re.compile(r"[a-z][a-z0-9']+")

EXPECTED_COMMENT_FIELDS = [
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

DEFAULT_STOPWORDS = {
    "a",
    "about",
    "after",
    "all",
    "also",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "been",
    "before",
    "but",
    "by",
    "can",
    "cant",
    "could",
    "did",
    "didnt",
    "do",
    "does",
    "doesnt",
    "doing",
    "dont",
    "for",
    "from",
    "get",
    "got",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "him",
    "his",
    "how",
    "i",
    "if",
    "im",
    "in",
    "into",
    "is",
    "isnt",
    "it",
    "its",
    "ive",
    "just",
    "me",
    "more",
    "most",
    "my",
    "no",
    "not",
    "now",
    "of",
    "on",
    "one",
    "only",
    "or",
    "our",
    "out",
    "please",
    "really",
    "so",
    "some",
    "still",
    "such",
    "than",
    "that",
    "thats",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "to",
    "too",
    "very",
    "was",
    "way",
    "we",
    "well",
    "were",
    "what",
    "when",
    "which",
    "who",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
    "yours",
    "mod",
    "mods",
    "game",
    "games",
    "dst",
    "dontstarve",
    "starve",
    "together",
    "steam",
    "workshop",
}


def tokenize_text(text: str | None, *, stopwords: set[str] | None = None) -> list[str]:
    if not text:
        return []
    active_stopwords = stopwords or DEFAULT_STOPWORDS
    tokens: list[str] = []
    for raw_token in ENGLISH_TOKEN_RE.findall(text.lower()):
        token = raw_token.strip("'")
        if len(token) < 2:
            continue
        if token in active_stopwords:
            continue
        tokens.append(token)
    return tokens


def rank_group_from_rank(rank: int) -> str:
    if rank <= 100:
        return "top_100"
    if 300 <= rank <= 500:
        return "rank_300_500"
    return "rank_101_299"


def percentile_disc(sorted_values: list[int], p: float) -> int | None:
    if not sorted_values:
        return None
    index = max(1, math.ceil(len(sorted_values) * p)) - 1
    return sorted_values[index]


def row_from_values(values: list[str]) -> dict[str, str]:
    row: dict[str, str] = {}
    for index, field in enumerate(EXPECTED_COMMENT_FIELDS):
        row[field] = values[index] if index < len(values) else ""
    return row


def load_comments_rows(path: Path, *, fallback_jsonl_path: Path | None = None) -> list[dict[str, str]]:
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.reader(csv_file)
            first_row = next(reader, None)
            if first_row is None:
                return []
            if first_row == EXPECTED_COMMENT_FIELDS:
                csv_file.seek(0)
                return [dict(row) for row in csv.DictReader(csv_file)]

        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.reader(csv_file)
            return [row_from_values(raw_row) for raw_row in reader if raw_row]

    if fallback_jsonl_path and fallback_jsonl_path.exists():
        rows: list[dict[str, str]] = []
        with fallback_jsonl_path.open("r", encoding="utf-8") as jsonl_file:
            for line in jsonl_file:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                rows.append(
                    {
                        field: "" if payload.get(field) is None else str(payload.get(field))
                        for field in EXPECTED_COMMENT_FIELDS
                    }
                )
        return rows

    raise FileNotFoundError(f"Comments file not found: {path}")


def build_group_summary(rows: list[dict[str, str]], groups: Iterable[str]) -> list[dict[str, object]]:
    group_set = set(groups)
    comment_counts = Counter()
    mod_sets: dict[str, set[str]] = {group: set() for group in group_set}
    for row in rows:
        group = row.get("rank_group")
        if group not in group_set:
            continue
        comment_counts[group] += 1
        if row.get("mod_id"):
            mod_sets[group].add(str(row["mod_id"]))

    summary_rows: list[dict[str, object]] = []
    for group in groups:
        summary_rows.append(
            {
                "rank_group": group,
                "comment_count": comment_counts[group],
                "mod_count": len(mod_sets[group]),
            }
        )
    return summary_rows


def compare_keywords(
    rows: list[dict[str, str]],
    *,
    left_group: str,
    right_group: str,
    min_comment_count: int = 5,
    stopwords: set[str] | None = None,
) -> list[dict[str, object]]:
    left_comment_total = 0
    right_comment_total = 0
    left_counter: Counter[str] = Counter()
    right_counter: Counter[str] = Counter()

    for row in rows:
        group = row.get("rank_group")
        if group not in {left_group, right_group}:
            continue
        unique_tokens = set(tokenize_text(row.get("content_text"), stopwords=stopwords))
        if not unique_tokens:
            continue
        if group == left_group:
            left_comment_total += 1
            left_counter.update(unique_tokens)
        else:
            right_comment_total += 1
            right_counter.update(unique_tokens)

    all_tokens = set(left_counter) | set(right_counter)
    comparison_rows: list[dict[str, object]] = []
    for token in all_tokens:
        left_count = left_counter[token]
        right_count = right_counter[token]
        if left_count + right_count < min_comment_count:
            continue
        left_rate = (left_count / left_comment_total * 1000) if left_comment_total else 0.0
        right_rate = (right_count / right_comment_total * 1000) if right_comment_total else 0.0
        rate_diff = left_rate - right_rate
        if left_rate > 0 and right_rate > 0:
            rate_ratio = left_rate / right_rate
        elif left_rate > 0:
            rate_ratio = None
        else:
            rate_ratio = 0.0
        dominant_group = left_group if rate_diff > 0 else right_group if rate_diff < 0 else "tie"
        comparison_rows.append(
            {
                "token": token,
                f"{left_group}_comment_count": left_count,
                f"{right_group}_comment_count": right_count,
                f"{left_group}_comments_per_1000": round(left_rate, 2),
                f"{right_group}_comments_per_1000": round(right_rate, 2),
                "comments_per_1000_diff": round(rate_diff, 2),
                "rate_ratio": round(rate_ratio, 4) if rate_ratio is not None else "",
                "dominant_group": dominant_group,
            }
        )

    comparison_rows.sort(
        key=lambda row: (
            -abs(float(row["comments_per_1000_diff"])),
            -(int(row[f"{left_group}_comment_count"]) + int(row[f"{right_group}_comment_count"])),
            str(row["token"]),
        )
    )
    return comparison_rows
