"""
data_validator.py — Post-pipeline data quality checks.

Each check returns a dict with keys: name, status ("pass" | "warn"), detail.
Validation failures do NOT block the pipeline; they produce WARNING-level logs.
Results are persisted to data/processed/validation_report_{batch_id}.json.
"""

from __future__ import annotations

import csv
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("pipeline.validator")


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_mod_count(csv_path: str | Path, lo: int, hi: int) -> dict[str, Any]:
    """Mod total should stay within a plausible range."""
    path = Path(csv_path)
    if not path.exists():
        return {"name": "mod_count_check", "status": "warn", "detail": f"CSV not found: {path}"}
    with open(path, encoding="utf-8") as f:
        count = sum(1 for _ in csv.reader(f)) - 1  # minus header
    ok = lo <= count <= hi
    return {
        "name": "mod_count_check",
        "status": "pass" if ok else "warn",
        "detail": f"mod_count={count}, expected [{lo}, {hi}]",
        "mod_count": count,
    }


def check_null_title_rate(csv_path: str | Path, max_pct: float) -> dict[str, Any]:
    """Title should almost never be NULL / empty."""
    path = Path(csv_path)
    if not path.exists():
        return {"name": "null_title_check", "status": "warn", "detail": f"CSV not found: {path}"}
    total = 0
    nulls = 0
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            title = row.get("title", "")
            if not title or title.strip() == "":
                nulls += 1
    pct = nulls / total if total else 0
    ok = pct <= max_pct
    return {
        "name": "null_title_check",
        "status": "pass" if ok else "warn",
        "detail": f"null_title_pct={pct:.4f} ({nulls}/{total}), threshold={max_pct}",
    }


def check_top10_stability(
    csv_path: str | Path,
    prev_csv_path: str | Path | None,
) -> dict[str, Any]:
    """Top-10 by subscriptions should not change completely between batches."""
    path = Path(csv_path)
    if not path.exists():
        return {"name": "top10_stability_check", "status": "warn", "detail": f"CSV not found: {path}"}

    def _top10_ids(p: Path) -> set[str]:
        rows: list[tuple[str, int]] = []
        with open(p, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    subs = int(row.get("subscriptions") or 0)
                except (ValueError, TypeError):
                    subs = 0
                rows.append((row.get("mod_id", ""), subs))
        rows.sort(key=lambda r: r[1], reverse=True)
        return {r[0] for r in rows[:10]}

    current = _top10_ids(path)
    if prev_csv_path is None or not Path(prev_csv_path).exists():
        return {
            "name": "top10_stability_check",
            "status": "pass",
            "detail": "No previous batch to compare against",
        }
    previous = _top10_ids(Path(prev_csv_path))
    overlap = len(current & previous)
    ok = overlap >= 5  # at least half should persist
    return {
        "name": "top10_stability_check",
        "status": "pass" if ok else "warn",
        "detail": f"overlap={overlap}/10 with previous batch",
    }


def check_comment_success_rate(
    checkpoint_path: str | Path | None,
    min_rate: float,
) -> dict[str, Any]:
    """Comment crawl should succeed for a reasonable fraction of target mods."""
    if checkpoint_path is None or not Path(checkpoint_path).exists():
        return {
            "name": "comment_success_rate",
            "status": "pass",
            "detail": "No comment checkpoint to check",
        }
    with open(checkpoint_path, encoding="utf-8") as f:
        ckpt = json.load(f)
    completed = len(ckpt.get("completed_mods", []))
    failed = len(ckpt.get("failed_mods", []))
    total = completed + failed
    rate = completed / total if total else 0
    ok = rate >= min_rate
    return {
        "name": "comment_success_rate",
        "status": "pass" if ok else "warn",
        "detail": f"success_rate={rate:.2f} ({completed}/{total}), threshold={min_rate}",
        "comment_success_rate": round(rate, 4),
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_all_checks(
    *,
    api_csv_path: str | Path | None = None,
    prev_api_csv_path: str | Path | None = None,
    comment_checkpoint_path: str | Path | None = None,
    mod_count_range: tuple[int, int] = (20_000, 30_000),
    max_null_title_pct: float = 0.01,
    min_comment_success_rate: float = 0.3,
) -> list[dict[str, Any]]:
    """Run every registered check and return results list."""
    results: list[dict[str, Any]] = []

    if api_csv_path:
        results.append(check_mod_count(api_csv_path, *mod_count_range))
        results.append(check_null_title_rate(api_csv_path, max_null_title_pct))
        results.append(check_top10_stability(api_csv_path, prev_api_csv_path))

    results.append(check_comment_success_rate(comment_checkpoint_path, min_comment_success_rate))

    for r in results:
        if r["status"] == "warn":
            logger.warning("VALIDATION WARNING: %s — %s", r["name"], r["detail"])
        else:
            logger.info("Validation pass: %s — %s", r["name"], r["detail"])

    return results


def save_report(results: list[dict[str, Any]], output_path: str | Path) -> None:
    """Persist validation report to JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info("Validation report saved → %s", path)
