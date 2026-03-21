-- Module 1: activity quadrant analysis for the latest Steam API batch.
-- Quadrant mapping:
--   evergreen = 常青树
--   hit_then_abandoned = 爆款弃坑
--   passion_project = 用爱发电
--   silent_fade = 沉默消亡
-- Rule: values strictly greater than the median are treated as "high".
--       values equal to or below the median are treated as "low".
-- Source note: rows missing subscriptions or created/updated timestamps are excluded from classification.

-- 1) Coverage check and median thresholds.
WITH latest_batch AS (
    SELECT batch_id
    FROM steam_api_mods_raw
    GROUP BY batch_id
    ORDER BY MAX(crawl_time_utc) DESC, batch_id DESC
    LIMIT 1
),
base AS (
    SELECT
        mod_id,
        subscriptions,
        time_created_utc,
        time_updated_utc,
        DATEDIFF(time_updated_utc, time_created_utc) AS maintenance_days,
        DATEDIFF(CURDATE(), time_updated_utc) AS days_since_last_update
    FROM steam_api_mods_raw
    WHERE batch_id = (SELECT batch_id FROM latest_batch)
),
valid AS (
    SELECT *
    FROM base
    WHERE subscriptions IS NOT NULL
      AND time_created_utc IS NOT NULL
      AND time_updated_utc IS NOT NULL
),
sub_ranked AS (
    SELECT
        subscriptions,
        ROW_NUMBER() OVER (ORDER BY subscriptions) AS rn,
        COUNT(*) OVER () AS cnt
    FROM valid
),
maint_ranked AS (
    SELECT
        maintenance_days,
        ROW_NUMBER() OVER (ORDER BY maintenance_days) AS rn,
        COUNT(*) OVER () AS cnt
    FROM valid
),
medians AS (
    SELECT
        (
            SELECT AVG(subscriptions)
            FROM sub_ranked
            WHERE rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2))
        ) AS subscription_median,
        (
            SELECT AVG(maintenance_days)
            FROM maint_ranked
            WHERE rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2))
        ) AS maintenance_median
)
SELECT
    (SELECT batch_id FROM latest_batch) AS batch_id,
    (SELECT COUNT(*) FROM base) AS total_mods,
    (SELECT COUNT(*) FROM valid) AS classified_mods,
    (SELECT COUNT(*) FROM base) - (SELECT COUNT(*) FROM valid) AS excluded_mods,
    subscription_median,
    maintenance_median,
    SUM(CASE WHEN maintenance_days = 0 THEN 1 ELSE 0 END) AS maintenance_eq_0_count,
    SUM(CASE WHEN maintenance_days = 1 THEN 1 ELSE 0 END) AS maintenance_eq_1_count,
    SUM(CASE WHEN maintenance_days > 1 THEN 1 ELSE 0 END) AS maintenance_gt_1_count,
    ROUND(AVG(days_since_last_update), 2) AS avg_days_since_last_update_all_classified
FROM valid
CROSS JOIN medians;

-- 2) Quadrant summary table for dashboarding.
WITH latest_batch AS (
    SELECT batch_id
    FROM steam_api_mods_raw
    GROUP BY batch_id
    ORDER BY MAX(crawl_time_utc) DESC, batch_id DESC
    LIMIT 1
),
base AS (
    SELECT
        mod_id,
        title,
        subscriptions,
        DATEDIFF(time_updated_utc, time_created_utc) AS maintenance_days,
        DATEDIFF(CURDATE(), time_updated_utc) AS days_since_last_update
    FROM steam_api_mods_raw
    WHERE batch_id = (SELECT batch_id FROM latest_batch)
),
valid AS (
    SELECT *
    FROM base
    WHERE subscriptions IS NOT NULL
      AND maintenance_days IS NOT NULL
),
sub_ranked AS (
    SELECT
        subscriptions,
        ROW_NUMBER() OVER (ORDER BY subscriptions) AS rn,
        COUNT(*) OVER () AS cnt
    FROM valid
),
maint_ranked AS (
    SELECT
        maintenance_days,
        ROW_NUMBER() OVER (ORDER BY maintenance_days) AS rn,
        COUNT(*) OVER () AS cnt
    FROM valid
),
medians AS (
    SELECT
        (
            SELECT AVG(subscriptions)
            FROM sub_ranked
            WHERE rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2))
        ) AS subscription_median,
        (
            SELECT AVG(maintenance_days)
            FROM maint_ranked
            WHERE rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2))
        ) AS maintenance_median,
        (SELECT COUNT(*) FROM steam_api_mods_raw WHERE batch_id = (SELECT batch_id FROM latest_batch)) AS total_mods,
        (SELECT COUNT(*) FROM valid) AS classified_mods
),
quadrants AS (
    SELECT
        v.mod_id,
        v.title,
        v.subscriptions,
        v.maintenance_days,
        v.days_since_last_update,
        CASE
            WHEN v.subscriptions > m.subscription_median AND v.maintenance_days > m.maintenance_median THEN 'evergreen'
            WHEN v.subscriptions > m.subscription_median AND v.maintenance_days <= m.maintenance_median THEN 'hit_then_abandoned'
            WHEN v.subscriptions <= m.subscription_median AND v.maintenance_days > m.maintenance_median THEN 'passion_project'
            ELSE 'silent_fade'
        END AS activity_quadrant
    FROM valid v
    CROSS JOIN medians m
)
SELECT
    activity_quadrant,
    COUNT(*) AS mod_count,
    ROUND(COUNT(*) / MAX(classified_mods) * 100, 2) AS pct_of_classified_mods,
    ROUND(COUNT(*) / MAX(total_mods) * 100, 2) AS pct_of_total_mods,
    ROUND(AVG(subscriptions), 2) AS avg_subscriptions,
    ROUND(AVG(days_since_last_update), 2) AS avg_days_since_last_update,
    ROUND(AVG(maintenance_days), 2) AS avg_maintenance_days
FROM quadrants
CROSS JOIN medians
GROUP BY activity_quadrant
ORDER BY FIELD(
    activity_quadrant,
    'evergreen',
    'hit_then_abandoned',
    'passion_project',
    'silent_fade'
);

-- 3) Tag split across quadrants.
-- This query explodes tags_json, removes version tags, de-duplicates mod-tag pairs,
-- and returns tag-level quadrant composition. Add HAVING / LIMIT as needed for reporting.
WITH latest_batch AS (
    SELECT batch_id
    FROM steam_api_mods_raw
    GROUP BY batch_id
    ORDER BY MAX(crawl_time_utc) DESC, batch_id DESC
    LIMIT 1
),
base AS (
    SELECT
        mod_id,
        subscriptions,
        DATEDIFF(time_updated_utc, time_created_utc) AS maintenance_days,
        tags_json
    FROM steam_api_mods_raw
    WHERE batch_id = (SELECT batch_id FROM latest_batch)
),
valid AS (
    SELECT *
    FROM base
    WHERE subscriptions IS NOT NULL
      AND maintenance_days IS NOT NULL
),
sub_ranked AS (
    SELECT
        subscriptions,
        ROW_NUMBER() OVER (ORDER BY subscriptions) AS rn,
        COUNT(*) OVER () AS cnt
    FROM valid
),
maint_ranked AS (
    SELECT
        maintenance_days,
        ROW_NUMBER() OVER (ORDER BY maintenance_days) AS rn,
        COUNT(*) OVER () AS cnt
    FROM valid
),
medians AS (
    SELECT
        (
            SELECT AVG(subscriptions)
            FROM sub_ranked
            WHERE rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2))
        ) AS subscription_median,
        (
            SELECT AVG(maintenance_days)
            FROM maint_ranked
            WHERE rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2))
        ) AS maintenance_median
),
quadrants AS (
    SELECT
        v.mod_id,
        CASE
            WHEN v.subscriptions > m.subscription_median AND v.maintenance_days > m.maintenance_median THEN 'evergreen'
            WHEN v.subscriptions > m.subscription_median AND v.maintenance_days <= m.maintenance_median THEN 'hit_then_abandoned'
            WHEN v.subscriptions <= m.subscription_median AND v.maintenance_days > m.maintenance_median THEN 'passion_project'
            ELSE 'silent_fade'
        END AS activity_quadrant
    FROM valid v
    CROSS JOIN medians m
),
expanded_tags AS (
    SELECT DISTINCT
        q.mod_id,
        q.activity_quadrant,
        jt.tag
    FROM quadrants q
    JOIN steam_api_mods_raw s
      ON s.mod_id = q.mod_id
     AND s.batch_id = (SELECT batch_id FROM latest_batch)
    JOIN JSON_TABLE(
        CAST(s.tags_json AS JSON),
        '$[*]' COLUMNS(tag VARCHAR(128) PATH '$.tag')
    ) jt
    WHERE s.tags_json IS NOT NULL
      AND JSON_VALID(s.tags_json) = 1
      AND s.tags_json <> '[]'
      AND jt.tag IS NOT NULL
      AND jt.tag <> ''
      AND jt.tag NOT LIKE 'version:%'
      AND jt.tag NOT LIKE 'version_compatible:%'
)
SELECT
    tag,
    COUNT(*) AS tag_mod_count,
    SUM(CASE WHEN activity_quadrant = 'evergreen' THEN 1 ELSE 0 END) AS evergreen_count,
    SUM(CASE WHEN activity_quadrant = 'hit_then_abandoned' THEN 1 ELSE 0 END) AS hit_then_abandoned_count,
    SUM(CASE WHEN activity_quadrant = 'passion_project' THEN 1 ELSE 0 END) AS passion_project_count,
    SUM(CASE WHEN activity_quadrant = 'silent_fade' THEN 1 ELSE 0 END) AS silent_fade_count,
    ROUND(AVG(CASE WHEN activity_quadrant = 'evergreen' THEN 1 ELSE 0 END) * 100, 2) AS evergreen_pct,
    ROUND(AVG(CASE WHEN activity_quadrant = 'hit_then_abandoned' THEN 1 ELSE 0 END) * 100, 2) AS hit_then_abandoned_pct,
    ROUND(AVG(CASE WHEN activity_quadrant = 'passion_project' THEN 1 ELSE 0 END) * 100, 2) AS passion_project_pct,
    ROUND(AVG(CASE WHEN activity_quadrant = 'silent_fade' THEN 1 ELSE 0 END) * 100, 2) AS silent_fade_pct
FROM expanded_tags
GROUP BY tag
ORDER BY tag_mod_count DESC, tag;

-- 4) Module 2: tag supply-demand matrix.
-- Supply axis: mod count per normalized tag.
-- Demand axis: median subscriptions per normalized tag.
-- Supporting metrics: average subscriptions and P75 subscriptions.
-- Normalization: lower-case tag values; exclude version tags.
-- Zone rule for stable tags:
--   blue_ocean = low supply + high demand
--   red_ocean = high supply + low demand
--   crowded_but_strong = high supply + high demand
--   cold_niche = low supply + low demand
-- Stable tags use a minimum sample size of 100 mods.
WITH latest_batch AS (
    SELECT batch_id
    FROM steam_api_mods_raw
    GROUP BY batch_id
    ORDER BY MAX(crawl_time_utc) DESC, batch_id DESC
    LIMIT 1
),
expanded_tags AS (
    SELECT DISTINCT
        s.mod_id,
        LOWER(TRIM(jt.tag)) AS normalized_tag,
        s.subscriptions
    FROM steam_api_mods_raw s
    JOIN JSON_TABLE(
        CAST(s.tags_json AS JSON),
        '$[*]' COLUMNS(tag VARCHAR(128) PATH '$.tag')
    ) jt
    WHERE s.batch_id = (SELECT batch_id FROM latest_batch)
      AND s.subscriptions IS NOT NULL
      AND s.tags_json IS NOT NULL
      AND JSON_VALID(s.tags_json) = 1
      AND s.tags_json <> '[]'
      AND jt.tag IS NOT NULL
      AND TRIM(jt.tag) <> ''
      AND LOWER(TRIM(jt.tag)) NOT LIKE 'version:%'
      AND LOWER(TRIM(jt.tag)) NOT LIKE 'version_compatible:%'
),
tag_ranked AS (
    SELECT
        normalized_tag AS tag,
        subscriptions,
        ROW_NUMBER() OVER (PARTITION BY normalized_tag ORDER BY subscriptions) AS rn,
        COUNT(*) OVER (PARTITION BY normalized_tag) AS cnt
    FROM expanded_tags
),
tag_stats AS (
    SELECT
        tag,
        MAX(cnt) AS mod_count,
        ROUND(AVG(subscriptions), 2) AS avg_subscriptions,
        ROUND(AVG(CASE WHEN rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2)) THEN subscriptions END), 2) AS median_subscriptions,
        MAX(CASE WHEN rn = CEIL(cnt * 0.75) THEN subscriptions END) AS p75_subscriptions
    FROM tag_ranked
    GROUP BY tag
),
stable_tags AS (
    SELECT *
    FROM tag_stats
    WHERE mod_count >= 100
),
supply_ranked AS (
    SELECT
        mod_count,
        ROW_NUMBER() OVER (ORDER BY mod_count) AS rn,
        COUNT(*) OVER () AS cnt
    FROM stable_tags
),
demand_ranked AS (
    SELECT
        median_subscriptions,
        ROW_NUMBER() OVER (ORDER BY median_subscriptions) AS rn,
        COUNT(*) OVER () AS cnt
    FROM stable_tags
),
p75_ranked AS (
    SELECT
        p75_subscriptions,
        ROW_NUMBER() OVER (ORDER BY p75_subscriptions) AS rn,
        COUNT(*) OVER () AS cnt
    FROM stable_tags
),
thresholds AS (
    SELECT
        (
            SELECT AVG(mod_count)
            FROM supply_ranked
            WHERE rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2))
        ) AS supply_median_threshold,
        (
            SELECT AVG(median_subscriptions)
            FROM demand_ranked
            WHERE rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2))
        ) AS demand_median_threshold,
        (
            SELECT AVG(p75_subscriptions)
            FROM p75_ranked
            WHERE rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2))
        ) AS p75_median_threshold
),
tag_matrix AS (
    SELECT
        s.tag,
        s.mod_count,
        s.avg_subscriptions,
        s.median_subscriptions,
        s.p75_subscriptions,
        t.supply_median_threshold,
        t.demand_median_threshold,
        t.p75_median_threshold,
        CASE
            WHEN s.mod_count < t.supply_median_threshold THEN 'low_supply'
            ELSE 'high_supply'
        END AS supply_side,
        CASE
            WHEN s.median_subscriptions > t.demand_median_threshold THEN 'high_demand'
            ELSE 'low_demand'
        END AS demand_side,
        CASE
            WHEN s.mod_count < t.supply_median_threshold AND s.median_subscriptions > t.demand_median_threshold THEN 'blue_ocean'
            WHEN s.mod_count > t.supply_median_threshold AND s.median_subscriptions < t.demand_median_threshold THEN 'red_ocean'
            WHEN s.mod_count > t.supply_median_threshold AND s.median_subscriptions > t.demand_median_threshold THEN 'crowded_but_strong'
            ELSE 'cold_niche'
        END AS market_zone
    FROM stable_tags s
    CROSS JOIN thresholds t
)
SELECT
    tag,
    mod_count,
    avg_subscriptions,
    median_subscriptions,
    p75_subscriptions,
    supply_median_threshold,
    demand_median_threshold,
    p75_median_threshold,
    supply_side,
    demand_side,
    market_zone
FROM tag_matrix
ORDER BY
    FIELD(market_zone, 'blue_ocean', 'crowded_but_strong', 'red_ocean', 'cold_niche'),
    median_subscriptions DESC,
    p75_subscriptions DESC,
    mod_count ASC,
    tag;

-- 5) Module 3: author productivity table.
-- Author identifier uses the Steam creator ID from the API `creator` field.
-- Metrics:
--   mod_count, total_subscriptions, avg_subscriptions, median_subscriptions,
--   avg_positive_rate, avg_maintenance_days, tag_breadth.
WITH latest_batch AS (
    SELECT batch_id
    FROM steam_api_mods_raw
    GROUP BY batch_id
    ORDER BY MAX(crawl_time_utc) DESC, batch_id DESC
    LIMIT 1
),
author_mods AS (
    SELECT
        creator AS creator_id,
        subscriptions,
        CASE
            WHEN votes_up IS NOT NULL AND votes_down IS NOT NULL AND (votes_up + votes_down) > 0
                THEN votes_up / (votes_up + votes_down)
            ELSE NULL
        END AS positive_rate,
        CASE
            WHEN time_created_utc IS NOT NULL AND time_updated_utc IS NOT NULL
                THEN DATEDIFF(time_updated_utc, time_created_utc)
            ELSE NULL
        END AS maintenance_days
    FROM steam_api_mods_raw
    WHERE batch_id = (SELECT batch_id FROM latest_batch)
      AND creator IS NOT NULL
),
author_ranked AS (
    SELECT
        creator_id,
        subscriptions,
        ROW_NUMBER() OVER (PARTITION BY creator_id ORDER BY subscriptions) AS rn,
        COUNT(*) OVER (PARTITION BY creator_id) AS cnt
    FROM author_mods
    WHERE subscriptions IS NOT NULL
),
author_medians AS (
    SELECT
        creator_id,
        ROUND(AVG(CASE WHEN rn IN (FLOOR((cnt + 1) / 2), FLOOR((cnt + 2) / 2)) THEN subscriptions END), 2) AS median_subscriptions
    FROM author_ranked
    GROUP BY creator_id
),
author_tag_breadth AS (
    SELECT
        s.creator AS creator_id,
        COUNT(DISTINCT LOWER(TRIM(jt.tag))) AS tag_breadth
    FROM steam_api_mods_raw s
    JOIN JSON_TABLE(
        CAST(s.tags_json AS JSON),
        '$[*]' COLUMNS(tag VARCHAR(128) PATH '$.tag')
    ) jt
    WHERE s.batch_id = (SELECT batch_id FROM latest_batch)
      AND s.creator IS NOT NULL
      AND s.tags_json IS NOT NULL
      AND JSON_VALID(s.tags_json) = 1
      AND s.tags_json <> '[]'
      AND jt.tag IS NOT NULL
      AND TRIM(jt.tag) <> ''
      AND LOWER(TRIM(jt.tag)) NOT LIKE 'version:%'
      AND LOWER(TRIM(jt.tag)) NOT LIKE 'version_compatible:%'
    GROUP BY s.creator
)
SELECT
    m.creator_id,
    COUNT(*) AS mod_count,
    SUM(m.subscriptions) AS total_subscriptions,
    ROUND(AVG(m.subscriptions), 2) AS avg_subscriptions,
    am.median_subscriptions,
    ROUND(AVG(m.positive_rate), 6) AS avg_positive_rate,
    ROUND(AVG(m.maintenance_days), 2) AS avg_maintenance_days,
    COALESCE(t.tag_breadth, 0) AS tag_breadth
FROM author_mods m
LEFT JOIN author_medians am ON am.creator_id = m.creator_id
LEFT JOIN author_tag_breadth t ON t.creator_id = m.creator_id
GROUP BY m.creator_id, am.median_subscriptions, t.tag_breadth
ORDER BY total_subscriptions DESC, mod_count DESC, m.creator_id;

-- 6) Module 3: head concentration.
WITH latest_batch AS (
    SELECT batch_id
    FROM steam_api_mods_raw
    GROUP BY batch_id
    ORDER BY MAX(crawl_time_utc) DESC, batch_id DESC
    LIMIT 1
),
author_mods AS (
    SELECT
        creator AS creator_id,
        subscriptions
    FROM steam_api_mods_raw
    WHERE batch_id = (SELECT batch_id FROM latest_batch)
      AND creator IS NOT NULL
),
author_stats AS (
    SELECT
        creator_id,
        COUNT(*) AS mod_count,
        SUM(subscriptions) AS total_subscriptions
    FROM author_mods
    GROUP BY creator_id
),
ranked AS (
    SELECT
        creator_id,
        mod_count,
        total_subscriptions,
        ROW_NUMBER() OVER (ORDER BY total_subscriptions DESC, mod_count DESC, creator_id) AS author_rank,
        COUNT(*) OVER () AS author_count,
        SUM(total_subscriptions) OVER () AS total_subscriptions_all
    FROM author_stats
)
SELECT
    MAX(author_count) AS author_count,
    CEIL(MAX(author_count) * 0.01) AS top_1pct_author_count,
    MAX(total_subscriptions_all) AS total_subscriptions_all,
    SUM(CASE WHEN author_rank <= CEIL(author_count * 0.01) THEN total_subscriptions ELSE 0 END) AS top_1pct_subscriptions,
    ROUND(SUM(CASE WHEN author_rank <= CEIL(author_count * 0.01) THEN total_subscriptions ELSE 0 END) / MAX(total_subscriptions_all) * 100, 2) AS top_1pct_share_pct,
    SUM(CASE WHEN author_rank <= 10 THEN total_subscriptions ELSE 0 END) AS top_10_subscriptions,
    ROUND(SUM(CASE WHEN author_rank <= 10 THEN total_subscriptions ELSE 0 END) / MAX(total_subscriptions_all) * 100, 2) AS top_10_share_pct
FROM ranked;

-- 7) Module 3: productivity vs. quality / performance.
-- Pearson correlation is used here for linear relationship checks.
WITH latest_batch AS (
    SELECT batch_id
    FROM steam_api_mods_raw
    GROUP BY batch_id
    ORDER BY MAX(crawl_time_utc) DESC, batch_id DESC
    LIMIT 1
),
author_mods AS (
    SELECT
        creator AS creator_id,
        subscriptions,
        CASE
            WHEN votes_up IS NOT NULL AND votes_down IS NOT NULL AND (votes_up + votes_down) > 0
                THEN votes_up / (votes_up + votes_down)
            ELSE NULL
        END AS positive_rate
    FROM steam_api_mods_raw
    WHERE batch_id = (SELECT batch_id FROM latest_batch)
      AND creator IS NOT NULL
),
author_stats AS (
    SELECT
        creator_id,
        COUNT(*) AS mod_count,
        AVG(subscriptions) AS avg_subscriptions,
        AVG(positive_rate) AS avg_positive_rate
    FROM author_mods
    GROUP BY creator_id
),
subs_corr_base AS (
    SELECT
        COUNT(*) AS n,
        SUM(mod_count) AS sum_x,
        SUM(avg_subscriptions) AS sum_y,
        SUM(mod_count * avg_subscriptions) AS sum_xy,
        SUM(mod_count * mod_count) AS sum_x2,
        SUM(avg_subscriptions * avg_subscriptions) AS sum_y2
    FROM author_stats
),
positive_corr_base AS (
    SELECT
        COUNT(*) AS n,
        SUM(mod_count) AS sum_x,
        SUM(avg_positive_rate) AS sum_y,
        SUM(mod_count * avg_positive_rate) AS sum_xy,
        SUM(mod_count * mod_count) AS sum_x2,
        SUM(avg_positive_rate * avg_positive_rate) AS sum_y2
    FROM author_stats
    WHERE avg_positive_rate IS NOT NULL
),
productivity_buckets AS (
    SELECT
        CASE
            WHEN mod_count = 1 THEN '1'
            WHEN mod_count BETWEEN 2 AND 3 THEN '2_3'
            WHEN mod_count BETWEEN 4 AND 9 THEN '4_9'
            ELSE '10_plus'
        END AS productivity_bucket,
        mod_count,
        avg_subscriptions,
        avg_positive_rate
    FROM author_stats
)
SELECT
    'pearson_modcount_vs_avg_subscriptions' AS metric,
    ROUND(
        (n * sum_xy - sum_x * sum_y) /
        NULLIF(SQRT((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)), 0),
        6
    ) AS metric_value
FROM subs_corr_base
UNION ALL
SELECT
    'pearson_modcount_vs_avg_positive_rate' AS metric,
    ROUND(
        (n * sum_xy - sum_x * sum_y) /
        NULLIF(SQRT((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)), 0),
        6
    ) AS metric_value
FROM positive_corr_base
UNION ALL
SELECT
    CONCAT('bucket_', productivity_bucket, '_avg_author_avg_subscriptions') AS metric,
    ROUND(AVG(avg_subscriptions), 2) AS metric_value
FROM productivity_buckets
GROUP BY productivity_bucket
UNION ALL
SELECT
    CONCAT('bucket_', productivity_bucket, '_avg_author_positive_rate') AS metric,
    ROUND(AVG(avg_positive_rate), 6) AS metric_value
FROM productivity_buckets
GROUP BY productivity_bucket;


-- 8) Module 4: comment text analysis cohort selection.
-- Use the latest API batch to rank mods by subscriptions, then keep Top 100 and rank 300-500.
WITH latest_batch AS (
    SELECT batch_id
    FROM steam_api_mods_raw
    GROUP BY batch_id
    ORDER BY MAX(crawl_time_utc) DESC, batch_id DESC
    LIMIT 1
), ranked_mods AS (
    SELECT
        mod_id,
        title,
        subscriptions,
        ROW_NUMBER() OVER (ORDER BY subscriptions DESC, mod_id ASC) AS subscription_rank
    FROM steam_api_mods_raw
    WHERE batch_id = (SELECT batch_id FROM latest_batch)
      AND subscriptions IS NOT NULL
)
SELECT
    mod_id,
    title,
    subscriptions,
    subscription_rank,
    CASE
        WHEN subscription_rank <= 100 THEN 'top_100'
        WHEN subscription_rank BETWEEN 300 AND 500 THEN 'rank_300_500'
        ELSE 'rank_101_299'
    END AS rank_group
FROM ranked_mods
WHERE subscription_rank <= 500
ORDER BY subscription_rank;
