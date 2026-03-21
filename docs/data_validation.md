# Data Validation

## Validation date

- Validation run date: 2026-03-19
- Validation scope: public DST Workshop browse page, item detail page, item comments page, Steam QueryFiles API sample, Steam QueryFiles resumable full collector, MySQL raw-table load

## Source checks

### Steam Web API

- Endpoint checked: `https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/`
- Result without API key: `403 Forbidden`
- Result with working API key on 2026-03-19: `200 OK`
- Sample batch produced: `api_validation_20260319`
- Sample size produced from API: `10` DST mod records
- Full-collector smoke batch produced: `api_full_smoke_20260319`
- Full batch produced: `api_full_20260319`
- Full batch size produced from API: `22,920` DST mod records across `230` pages
- Smoke test verified:
  - `cursor=*` returns `next_cursor`
  - checkpoint file can store `page` and `cursor`
  - append-only CSV and JSONL writing works
- Full run verified:
  - checkpoint marks `completed=true`
  - CSV row count matches manifest `items_collected`
  - raw API data can contain blank `title`, occasional blank `creator`, and one near-empty row with blank `consumer_appid`

### Public workshop browse page

- Source pattern: `https://steamcommunity.com/workshop/browse/?appid=322330&section=readytouseitems`
- Verified fields on 2026-03-19:
  - `data-publishedfileid`
  - item title
  - detail URL
  - preview image URL
  - total entry count from paging info
- Observed count on 2026-03-19: `22,905` entries across `764` pages at 30 items per page

### Public workshop detail page

- Verified fields:
  - title
  - description
  - tags
  - owner Steam ID from embedded page data
  - creator display names and profile URLs from creator blocks
  - unique visitors
  - current subscribers
  - current favorites
  - ratings count
  - file size
  - posted time
  - updated time

### Public workshop comments page

- Verified fields:
  - comment ID
  - commenter display name
  - commenter profile URL
  - Unix timestamp from `data-timestamp`
  - comment text
- Current limitation:
  - comment vote counts were not found in a stable public selector

## Assumptions

- Detail-page `Posted` and `Updated` values are parsed from the visible workshop page text.
- Because the public detail-page timestamps do not expose an explicit timezone in the displayed field, the scraper stores both the raw text and a parsed naive datetime string.
- API exports now store both raw Unix epoch values and derived UTC ISO timestamps for created/updated times.
- The resumable full collector uses Steam's `next_cursor` as the authoritative continuation token and stores the local page counter only for progress tracking.
- Raw API ingestion preserves source gaps. The MySQL raw table allows `NULL` for fields that are not stable in the source, including `title` and `consumer_appid`.

## Output locations

- Public HTML raw sample: `data/raw/steam_workshop/validation_20260319/`
- Public HTML processed sample: `data/processed/steam_workshop/validation_20260319/`
- API raw sample: `data/raw/steam_api/api_validation_20260319/`
- API processed sample: `data/processed/steam_api/api_validation_20260319/`
- API full smoke raw: `data/raw/steam_api/api_full_smoke_20260319/`
- API full smoke processed: `data/processed/steam_api/api_full_smoke_20260319/`
- API full raw: `data/raw/steam_api/api_full_20260319/`
- API full processed: `data/processed/steam_api/api_full_20260319/`

## Recommended next step

- Build the cleaning layer on top of API data as the primary mod metadata source.
- Keep public HTML scraping as a fallback path and for comments.
- Add post-load validation SQL for row counts, null-rate checks, and duplicate-key checks.

### Public workshop comments at scale

- Batch produced on 2026-03-19: `top500_comments_20260319`
- Input selection source: latest `steam_api_mods_raw` batch ranked by `subscriptions`
- Selection size: `500` mods
- Collection scope: first `2` public comment pages per mod
- Comments collected: `17,782`
- Failed mods during comment fetch: `301`
- Main failure mode: Steam public pages returned repeated `429` responses
- Current interpretation boundary:
  - Comment text findings are based on the successfully collected subset, not on a fully complete top-500 census
  - Keyword comparison currently reflects English-tokenizable comments only
- Collector robustness fix applied on 2026-03-19:
  - `top_comments.csv` header writing was corrected to avoid BOM-only empty-file edge cases
  - The existing batch CSV was rebuilt from `top_comments.jsonl` to restore a valid header row

## Additional output locations

- Top-500 comment raw HTML: `data/raw/steam_workshop/top500_comments_20260319/`
- Top-500 comment processed files: `data/processed/steam_workshop/top500_comments_20260319/`
- Comment analysis outputs: `data/processed/analysis/`
