# Power BI Dashboard Build Guide

This folder stores build notes and screenshots for the 5-page Power BI dashboard.

## Exported datasets

Run the dashboard export first:

```bash
python scripts/06_export_powerbi_dashboard.py --host 127.0.0.1 --port 3306 --user root --password <MYSQL_PASSWORD> --database steamDST
```

The script writes a dated export folder under:

```text
data/processed/dashboard/powerbi_<YYYYMMDD>/
```

Main files:
- `overview_kpis.csv`
- `dim_tags.csv`
- `activity_mods.csv`
- `activity_mod_tags.csv`
- `supply_demand_tags.csv`
- `comments_group_summary.csv`
- `comments_keyword_comparison.csv`
- `comments_top_keywords.csv`
- `authors_productivity.csv`
- `authors_concentration_summary.csv`
- `authors_concentration_curve.csv`
- `authors_bucket_summary.csv`
- `authors_top_20.csv`

## Power BI relationships

Recommended model:
- `activity_mods[mod_id]` 1:* `activity_mod_tags[mod_id]`
- `dim_tags[tag]` 1:* `activity_mod_tags[tag]`
- `dim_tags[tag]` 1:* `supply_demand_tags[tag]`

Other tables can remain disconnected if used only inside a single page:
- `overview_kpis`
- `comments_group_summary`
- `comments_keyword_comparison`
- `comments_top_keywords`
- `authors_concentration_summary`
- `authors_concentration_curve`
- `authors_bucket_summary`
- `authors_top_20`

## Page plan

### 1. Overview
- Cards:
  - `overview_kpis[display_value]`
- Word cloud:
  - Category: `dim_tags[tag]`
  - Weight: `dim_tags[wordcloud_weight]`

### 2. Activity
- Scatter:
  - Details: `activity_mods[mod_id]`
  - X: `activity_mods[subscriptions]`
  - Y: `activity_mods[maintenance_days]`
  - Size: `activity_mods[votes_up]`
  - Legend: `activity_mods[quadrant_label]`
- Optional slicer:
  - `dim_tags[tag]`

### 3. Supply Demand
- Scatter:
  - Details: `supply_demand_tags[tag]`
  - X: `supply_demand_tags[mod_count]`
  - Y: `supply_demand_tags[median_subscriptions]`
  - Size: `supply_demand_tags[p75_subscriptions]`
  - Legend: `supply_demand_tags[market_zone]`

### 4. Comments
- Diverging bar chart or clustered bar chart:
  - Category: `comments_top_keywords[token]`
  - Series or legend: `comments_top_keywords[dominant_group]`
  - Value: `comments_top_keywords[comments_per_1000_diff]`
- Coverage cards:
  - `comments_group_summary[selected_mod_count]`
  - `comments_group_summary[mods_with_comments]`
  - `comments_group_summary[comment_count]`
  - `comments_group_summary[tokenized_comment_count]`

### 5. Authors
- Concentration chart:
  - X: `authors_concentration_curve[author_rank]`
  - Y: `authors_concentration_curve[cumulative_share_pct]`
  - Legend: `authors_concentration_curve[concentration_band]`
- Ranking table:
  - `authors_top_20[author_rank]`
  - `authors_top_20[creator_id]`
  - `authors_top_20[mod_count]`
  - `authors_top_20[total_subscriptions]`
  - `authors_top_20[avg_subscriptions]`
  - `authors_top_20[avg_positive_rate]`
  - `authors_top_20[productivity_bucket]`

## Screenshot output

Store exported screenshots in:

```text
dashboard/screenshots/
```
