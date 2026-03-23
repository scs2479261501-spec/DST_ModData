#!/usr/bin/env python3
"""
pipeline.py — One-command ETL orchestrator for the DST Mod Data project.

Usage:
    python scripts/pipeline.py                     # run all stages
    python scripts/pipeline.py --stage collect      # collect only
    python scripts/pipeline.py --stage analyze      # analyze only
    python scripts/pipeline.py --stage export       # export + build only
    python scripts/pipeline.py --batch-id 20260323  # explicit batch id

Stages (in order):
    collect   → collect_api, collect_comments, import_mysql
    analyze   → quadrant / supply-demand / author / comment analysis
    export    → dashboard CSV, site JSON, site build
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Ensure the scripts/ directory is importable
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import yaml  # PyYAML — listed in requirements

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or SCRIPTS_DIR / "pipeline_config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def env_or_default(cfg_section: dict, key_env_field: str, defaults: dict | None = None, field_name: str | None = None) -> str:
    """Read value from env var named in config, falling back to defaults dict."""
    env_name = cfg_section.get(key_env_field, "")
    val = os.environ.get(env_name, "")
    if val:
        return val
    if defaults and field_name:
        return str(defaults.get(field_name, ""))
    return ""


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(batch_id: str) -> None:
    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / f"pipeline_{batch_id}.log"
    fmt = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(ch)


logger = logging.getLogger("pipeline")


# ---------------------------------------------------------------------------
# Stage execution helper
# ---------------------------------------------------------------------------

class StageResult:
    """Collects timing and metadata for a single stage."""

    def __init__(self, name: str):
        self.name = name
        self.status = "pending"
        self.start: float = 0
        self.end: float = 0
        self.meta: dict[str, Any] = {}

    def begin(self) -> "StageResult":
        self.status = "running"
        self.start = time.time()
        logger.info("═══ STAGE [%s] START ═══", self.name)
        return self

    def succeed(self, **meta: Any) -> "StageResult":
        self.status = "success"
        self.end = time.time()
        self.meta.update(meta)
        logger.info(
            "═══ STAGE [%s] DONE ═══  (%.1fs)",
            self.name,
            self.end - self.start,
        )
        return self

    def fail(self, error: str) -> "StageResult":
        self.status = "failed"
        self.end = time.time()
        self.meta["error"] = error
        logger.error(
            "═══ STAGE [%s] FAILED ═══  %s  (%.1fs)",
            self.name,
            error,
            self.end - self.start,
        )
        return self

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 1) if self.end else 0

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"status": self.status, "duration": self.duration}
        d.update(self.meta)
        return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_latest_api_batch(processed_dir: Path) -> str | None:
    """Return the latest api_full batch directory name (by date token)."""
    api_dir = processed_dir / "steam_api"
    if not api_dir.exists():
        return None
    batches = sorted(
        [d.name for d in api_dir.iterdir() if d.is_dir()],
        reverse=True,
    )
    return batches[0] if batches else None


def find_latest_comment_batch(processed_dir: Path) -> str | None:
    """Return the latest comment collection batch directory name."""
    ws_dir = processed_dir / "steam_workshop"
    if not ws_dir.exists():
        return None
    batches = sorted(
        [d.name for d in ws_dir.iterdir() if d.is_dir() and "comment" in d.name.lower()],
        reverse=True,
    )
    return batches[0] if batches else None


def find_prev_api_csv(processed_dir: Path, current_batch: str) -> Path | None:
    """Find the API CSV from the batch before `current_batch`."""
    api_dir = processed_dir / "steam_api"
    if not api_dir.exists():
        return None
    batches = sorted([d.name for d in api_dir.iterdir() if d.is_dir()], reverse=True)
    for b in batches:
        if b != current_batch:
            candidate = api_dir / b / "mods_api_full.csv"
            if candidate.exists():
                return candidate
    return None


def run_script(script_name: str, args: list[str]) -> subprocess.CompletedProcess:
    """Run a sibling Python script as a subprocess."""
    script_path = SCRIPTS_DIR / script_name
    cmd = [sys.executable, str(script_path)] + args
    logger.info("  → %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    if result.stdout:
        for line in result.stdout.strip().splitlines():
            logger.debug("  [stdout] %s", line)
    if result.stderr:
        for line in result.stderr.strip().splitlines():
            logger.debug("  [stderr] %s", line)
    if result.returncode != 0:
        raise RuntimeError(
            f"{script_name} exited with code {result.returncode}.\n"
            f"stderr: {result.stderr[-2000:] if result.stderr else '(empty)'}"
        )
    return result


def mysql_args(cfg: dict) -> list[str]:
    """Build common MySQL CLI args from config."""
    my = cfg["mysql"]
    defaults = my.get("defaults", {})
    return [
        "--host", env_or_default(my, "host_env", defaults, "host") or "127.0.0.1",
        "--port", env_or_default(my, "port_env", defaults, "port") or "3306",
        "--user", env_or_default(my, "user_env", defaults, "user") or "root",
        "--password", env_or_default(my, "password_env", defaults, "password") or "",
        "--database", env_or_default(my, "database_env", defaults, "database") or "steamDST",
    ]


# ---------------------------------------------------------------------------
# Stage: COLLECT
# ---------------------------------------------------------------------------

def stage_collect_api(cfg: dict, batch_id: str) -> StageResult:
    """Full Steam API collection."""
    sr = StageResult("collect_api").begin()
    try:
        api_key = os.environ.get(cfg["steam_api"]["api_key_env"], "")
        if not api_key:
            raise RuntimeError(
                f"Environment variable {cfg['steam_api']['api_key_env']} is not set. "
                "Cannot collect API data without a Steam Web API key."
            )
        args = [
            "--api-key", api_key,
            "--app-id", str(cfg["steam_api"]["app_id"]),
            "--num-per-page", str(cfg["steam_api"]["num_per_page"]),
            "--sleep-seconds", str(cfg["steam_api"]["request_delay"]),
            "--batch-id", batch_id,
        ]
        run_script("02_collect_api_full.py", args)

        # Count output rows
        csv_path = PROJECT_ROOT / cfg["paths"]["processed_data"] / "steam_api" / batch_id / "mods_api_full.csv"
        mod_count = 0
        if csv_path.exists():
            with open(csv_path, encoding="utf-8") as f:
                mod_count = sum(1 for _ in csv.reader(f)) - 1
        return sr.succeed(mod_count=mod_count, csv_path=str(csv_path))
    except Exception as exc:
        return sr.fail(str(exc))


def stage_collect_comments(cfg: dict, batch_id: str) -> StageResult:
    """Incremental comment collection for top-N mods."""
    sr = StageResult("collect_comments").begin()
    try:
        comment_batch_id = f"top{cfg['collect']['comment_top_n']}_comments_{batch_id}"
        args = [
            "--top-n", str(cfg["collect"]["comment_top_n"]),
            "--comment-pages", str(cfg["collect"]["comment_pages_per_mod"]),
            "--sleep-seconds", str(cfg["collect"]["comment_request_delay"]),
            "--batch-id", comment_batch_id,
        ] + mysql_args(cfg)
        run_script("04_collect_top_comments.py", args)

        # Read checkpoint for stats
        ckpt_path = (
            PROJECT_ROOT / cfg["paths"]["raw_data"] / "steam_workshop" / comment_batch_id / "checkpoint.json"
        )
        new_comments = 0
        if ckpt_path.exists():
            with open(ckpt_path, encoding="utf-8") as f:
                ckpt = json.load(f)
            new_comments = ckpt.get("comments_collected", 0)
        return sr.succeed(new_comments=new_comments, comment_batch_id=comment_batch_id)
    except Exception as exc:
        return sr.fail(str(exc))


def stage_import_mysql(cfg: dict, batch_id: str) -> StageResult:
    """Import API CSV into MySQL with UPSERT."""
    sr = StageResult("import_mysql").begin()
    try:
        csv_path = PROJECT_ROOT / cfg["paths"]["processed_data"] / "steam_api" / batch_id / "mods_api_full.csv"
        if not csv_path.exists():
            raise RuntimeError(f"API CSV not found at {csv_path}")
        args = [
            "--csv-path", str(csv_path),
            "--table", cfg["mysql"].get("table", "steam_api_mods_raw"),
            "--chunk-size", str(cfg["mysql"].get("chunk_size", 500)),
        ] + mysql_args(cfg)
        run_script("03_import_api_csv_to_mysql.py", args)

        row_count = 0
        with open(csv_path, encoding="utf-8") as f:
            row_count = sum(1 for _ in csv.reader(f)) - 1
        return sr.succeed(rows_upserted=row_count)
    except Exception as exc:
        return sr.fail(str(exc))


# ---------------------------------------------------------------------------
# Stage: ANALYZE
# ---------------------------------------------------------------------------

def stage_analyze(cfg: dict, batch_id: str) -> StageResult:
    """Run analysis scripts: comment text analysis + SQL-based analysis via dashboard export."""
    sr = StageResult("analyze").begin()
    try:
        # Comment text analysis — find the latest comment batch
        processed = PROJECT_ROOT / cfg["paths"]["processed_data"]
        comment_batch = find_latest_comment_batch(processed)

        if comment_batch:
            logger.info("  Running comment text analysis for batch: %s", comment_batch)
            args = [
                "--batch-id", comment_batch,
                "--min-comment-count", str(cfg["analysis"].get("comment_min_count", 8)),
                "--top-keywords", str(cfg["analysis"].get("comment_top_keywords", 25)),
            ]
            run_script("05_analyze_comment_text.py", args)
        else:
            logger.info("  No comment batch found, skipping comment text analysis")

        # The heavy SQL-based analysis (quadrant, supply-demand, author productivity)
        # is performed inside 06_export_powerbi_dashboard.py as part of the export stage.
        # The analysis_queries.sql provides reference queries; the dashboard export script
        # does equivalent work and produces the analysis CSV outputs.
        return sr.succeed(comment_batch=comment_batch or "none")
    except Exception as exc:
        return sr.fail(str(exc))


# ---------------------------------------------------------------------------
# Stage: EXPORT
# ---------------------------------------------------------------------------

def stage_export_dashboard(cfg: dict, batch_id: str) -> StageResult:
    """Export Power BI dashboard CSVs."""
    sr = StageResult("export_dashboard").begin()
    try:
        output_batch = f"powerbi_{batch_id}"
        args = [
            "--output-batch-id", output_batch,
        ] + mysql_args(cfg)

        # Let the script auto-detect api and comment batch ids
        run_script("06_export_powerbi_dashboard.py", args)
        return sr.succeed(output_batch=output_batch)
    except Exception as exc:
        return sr.fail(str(exc))


def stage_export_site(cfg: dict, batch_id: str) -> StageResult:
    """Export site JSON data files from dashboard CSVs."""
    sr = StageResult("export_site").begin()
    try:
        site_data_dir = PROJECT_ROOT / cfg["paths"]["site_data"]
        site_data_dir.mkdir(parents=True, exist_ok=True)

        # Find latest dashboard batch
        dashboard_dir = PROJECT_ROOT / cfg["paths"]["dashboard_output"]
        if not dashboard_dir.exists():
            raise RuntimeError(f"Dashboard output directory not found: {dashboard_dir}")

        batches = sorted([d.name for d in dashboard_dir.iterdir() if d.is_dir()], reverse=True)
        if not batches:
            raise RuntimeError("No dashboard batches found")
        latest_db = batches[0]
        db_path = dashboard_dir / latest_db

        # Check if 08_export_site_data.py exists
        site_export_script = SCRIPTS_DIR / "08_export_site_data.py"
        if site_export_script.exists():
            logger.info("  Running 08_export_site_data.py")
            run_script("08_export_site_data.py", ["--dashboard-batch", latest_db])
        else:
            # The site expects a compact {meta, fields, items} JSON format
            # produced by 08_export_site_data.py. The fallback CSV→JSON
            # conversion produces a flat array which breaks the frontend.
            # Skip rather than corrupt existing site data.
            logger.info("  No 08_export_site_data.py found — skipping site data export")
            logger.info("  (existing site JSON files in %s are preserved)", site_data_dir)

        return sr.succeed(dashboard_batch=latest_db)
    except Exception as exc:
        return sr.fail(str(exc))


def stage_build_site(cfg: dict, batch_id: str) -> StageResult:
    """npm run build in site/ and copy output to docs/."""
    sr = StageResult("build_site").begin()
    try:
        site_dir = PROJECT_ROOT / cfg["paths"]["site_dir"]
        docs_dir = PROJECT_ROOT / cfg["paths"]["docs_dir"]

        if not (site_dir / "package.json").exists():
            logger.info("  No site/package.json found, skipping site build")
            return sr.succeed(skipped=True)

        logger.info("  Running npm run build in %s", site_dir)
        result = subprocess.run(
            ["npm", "run", "build"],
            capture_output=True, text=True, cwd=str(site_dir),
            shell=True,  # needed on Windows for npm
        )
        if result.returncode != 0:
            raise RuntimeError(f"npm run build failed:\n{result.stderr[-2000:]}")

        logger.info("  Site built successfully")

        # Vite outputs to ../docs relative to site/, so docs/ should already be updated.
        # Verify index.html exists
        if (docs_dir / "index.html").exists():
            logger.info("  docs/index.html confirmed present")
        else:
            logger.warning("  docs/index.html not found after build!")

        return sr.succeed()
    except Exception as exc:
        return sr.fail(str(exc))


# ---------------------------------------------------------------------------
# Validation stage
# ---------------------------------------------------------------------------

def stage_validate(cfg: dict, batch_id: str, stages: dict[str, StageResult]) -> StageResult:
    """Run data quality checks."""
    sr = StageResult("validate").begin()
    try:
        from data_validator import run_all_checks, save_report

        processed = PROJECT_ROOT / cfg["paths"]["processed_data"]
        val_cfg = cfg.get("validation", {})

        # Find current API CSV
        api_csv = None
        collect_result = stages.get("collect_api")
        if collect_result and collect_result.meta.get("csv_path"):
            api_csv = collect_result.meta["csv_path"]
        else:
            latest_batch = find_latest_api_batch(processed)
            if latest_batch:
                candidate = processed / "steam_api" / latest_batch / "mods_api_full.csv"
                if candidate.exists():
                    api_csv = str(candidate)

        # Find previous API CSV
        prev_csv = None
        latest_batch = find_latest_api_batch(processed)
        if latest_batch:
            prev_csv = find_prev_api_csv(processed, latest_batch)

        # Find comment checkpoint
        comment_ckpt = None
        comment_result = stages.get("collect_comments")
        if comment_result and comment_result.meta.get("comment_batch_id"):
            cb = comment_result.meta["comment_batch_id"]
            candidate = processed.parent / cfg["paths"]["raw_data"] / "steam_workshop" / cb / "checkpoint.json"
            if candidate.exists():
                comment_ckpt = str(candidate)

        results = run_all_checks(
            api_csv_path=api_csv,
            prev_api_csv_path=str(prev_csv) if prev_csv else None,
            comment_checkpoint_path=comment_ckpt,
            mod_count_range=tuple(val_cfg.get("mod_count_range", [20000, 30000])),
            max_null_title_pct=val_cfg.get("max_null_title_pct", 0.01),
            min_comment_success_rate=val_cfg.get("min_comment_success_rate", 0.3),
        )

        report_path = processed / f"validation_report_{batch_id}.json"
        save_report(results, report_path)

        validation_summary = {r["name"]: r["status"] for r in results}
        # Propagate comment_success_rate if present
        for r in results:
            if r.get("comment_success_rate") is not None:
                validation_summary["comment_success_rate"] = r["comment_success_rate"]

        return sr.succeed(validation=validation_summary)
    except Exception as exc:
        return sr.fail(str(exc))


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def write_summary(batch_id: str, total_start: float, stages: dict[str, StageResult], validation: dict) -> None:
    total_duration = round(time.time() - total_start, 1)
    summary = {
        "batch_id": batch_id,
        "total_duration_seconds": total_duration,
        "stages": {name: sr.to_dict() for name, sr in stages.items()},
        "validation": validation,
    }

    # Write to file
    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    summary_path = logs_dir / f"summary_{batch_id}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Print to console
    logger.info("")
    logger.info("╔══════════════════════════════════════════════════╗")
    logger.info("║           PIPELINE SUMMARY — %s           ║", batch_id)
    logger.info("╠══════════════════════════════════════════════════╣")
    for name, sr in stages.items():
        icon = "✓" if sr.status == "success" else "✗" if sr.status == "failed" else "—"
        logger.info("║  %s %-22s %8s  %6.1fs  ║", icon, name, sr.status, sr.duration)
    logger.info("╠══════════════════════════════════════════════════╣")
    logger.info("║  Total duration: %8.1fs                      ║", total_duration)
    if validation:
        for k, v in validation.items():
            logger.info("║  %-26s %20s  ║", k, v)
    logger.info("╚══════════════════════════════════════════════════╝")
    logger.info("Summary written → %s", summary_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DST Mod Data ETL Pipeline")
    p.add_argument(
        "--stage",
        choices=["collect", "analyze", "export", "all"],
        default="all",
        help="Which stage group to run (default: all)",
    )
    p.add_argument(
        "--batch-id",
        default=None,
        help="Explicit batch ID (default: YYYYMMDD of today UTC)",
    )
    p.add_argument(
        "--config",
        default=None,
        help="Path to pipeline_config.yaml (default: scripts/pipeline_config.yaml)",
    )
    p.add_argument(
        "--skip-comments",
        action="store_true",
        help="Skip comment collection (useful for quick runs)",
    )
    p.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip site build step",
    )
    return p


def main() -> int:
    args = build_parser().parse_args()

    batch_id = args.batch_id or datetime.now(timezone.utc).strftime("%Y%m%d")
    cfg = load_config(Path(args.config) if args.config else None)

    setup_logging(batch_id)
    logger.info("Pipeline started — batch_id=%s, stage=%s", batch_id, args.stage)

    total_start = time.time()
    stages: dict[str, StageResult] = {}
    failed = False

    # ------------------------------------------------------------------
    # COLLECT group
    # ------------------------------------------------------------------
    if args.stage in ("collect", "all") and not failed:
        # 1) API collection
        sr = stage_collect_api(cfg, batch_id)
        stages["collect_api"] = sr
        if sr.status == "failed":
            failed = True

        # 2) Import to MySQL
        if not failed:
            sr = stage_import_mysql(cfg, batch_id)
            stages["import_mysql"] = sr
            if sr.status == "failed":
                failed = True

        # 3) Comment collection
        if not failed and not args.skip_comments:
            sr = stage_collect_comments(cfg, batch_id)
            stages["collect_comments"] = sr
            if sr.status == "failed":
                # Comment failure is non-fatal — warn but continue
                logger.warning("Comment collection failed, continuing pipeline")
                failed = False

    # ------------------------------------------------------------------
    # ANALYZE group
    # ------------------------------------------------------------------
    if args.stage in ("analyze", "all") and not failed:
        sr = stage_analyze(cfg, batch_id)
        stages["analyze"] = sr
        if sr.status == "failed":
            failed = True

    # ------------------------------------------------------------------
    # EXPORT group
    # ------------------------------------------------------------------
    if args.stage in ("export", "all") and not failed:
        sr = stage_export_dashboard(cfg, batch_id)
        stages["export_dashboard"] = sr
        if sr.status == "failed":
            failed = True

        if not failed:
            sr = stage_export_site(cfg, batch_id)
            stages["export_site"] = sr
            if sr.status == "failed":
                failed = True

        if not failed and not args.skip_build:
            sr = stage_build_site(cfg, batch_id)
            stages["build_site"] = sr
            if sr.status == "failed":
                # Build failure is non-fatal
                logger.warning("Site build failed, continuing to validation")

    # ------------------------------------------------------------------
    # VALIDATION (always runs if there's data)
    # ------------------------------------------------------------------
    validation = {}
    sr = stage_validate(cfg, batch_id, stages)
    stages["validate"] = sr
    if sr.status == "success":
        validation = sr.meta.get("validation", {})

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    write_summary(batch_id, total_start, stages, validation)

    if failed:
        logger.error("Pipeline finished WITH ERRORS for batch %s", batch_id)
        return 1
    logger.info("Pipeline finished SUCCESSFULLY for batch %s", batch_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
