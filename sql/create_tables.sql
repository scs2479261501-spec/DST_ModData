-- Raw ingestion tables for the initial public-workshop scraping phase.
-- Detail-page posted/updated timestamps come from visible page text and are stored as naive datetimes.

CREATE TABLE IF NOT EXISTS crawl_batches (
    batch_id VARCHAR(64) PRIMARY KEY,
    source_method VARCHAR(64) NOT NULL,
    started_at_utc DATETIME NOT NULL,
    completed_at_utc DATETIME NULL,
    browse_pages_requested INT NOT NULL,
    max_items_requested INT NOT NULL,
    fetch_comments TINYINT(1) NOT NULL,
    comment_item_limit INT NOT NULL,
    comment_pages_requested INT NOT NULL,
    notes TEXT NULL
);

CREATE TABLE IF NOT EXISTS workshop_mods_raw (
    batch_id VARCHAR(64) NOT NULL,
    mod_id BIGINT NOT NULL,
    discover_page INT NOT NULL,
    discover_rank INT NOT NULL,
    title VARCHAR(500) NULL,
    detail_url TEXT NOT NULL,
    preview_image_url TEXT NULL,
    owner_steam_id BIGINT NULL,
    creator_display_names TEXT NULL,
    creator_profile_urls TEXT NULL,
    creator_miniprofile_ids TEXT NULL,
    tags_json TEXT NULL,
    description_text LONGTEXT NULL,
    description_length INT NOT NULL,
    unique_visitors BIGINT NULL,
    current_subscribers BIGINT NULL,
    current_favorites BIGINT NULL,
    ratings_count BIGINT NULL,
    votes_up BIGINT NULL,
    votes_down BIGINT NULL,
    score DECIMAL(12,10) NULL,
    file_size_text VARCHAR(64) NULL,
    file_size_bytes BIGINT NULL,
    posted_text VARCHAR(64) NULL,
    updated_text VARCHAR(64) NULL,
    posted_at_naive DATETIME NULL,
    updated_at_naive DATETIME NULL,
    crawl_time_utc DATETIME NOT NULL,
    raw_detail_path TEXT NOT NULL,
    PRIMARY KEY (batch_id, mod_id),
    INDEX idx_workshop_mods_raw_mod_id (mod_id),
    CONSTRAINT fk_workshop_mods_raw_batch
        FOREIGN KEY (batch_id) REFERENCES crawl_batches(batch_id)
);

CREATE TABLE IF NOT EXISTS workshop_comments_raw (
    batch_id VARCHAR(64) NOT NULL,
    comment_id BIGINT NOT NULL,
    mod_id BIGINT NOT NULL,
    comment_page INT NOT NULL,
    commenter_name VARCHAR(255) NULL,
    commenter_profile_url TEXT NULL,
    commenter_steam_id BIGINT NULL,
    commenter_miniprofile_id BIGINT NULL,
    comment_timestamp_epoch BIGINT NULL,
    comment_timestamp_utc DATETIME NULL,
    comment_timestamp_text VARCHAR(64) NULL,
    content_text LONGTEXT NULL,
    content_html LONGTEXT NULL,
    crawl_time_utc DATETIME NOT NULL,
    raw_comments_path TEXT NOT NULL,
    PRIMARY KEY (batch_id, comment_id),
    INDEX idx_workshop_comments_raw_mod_id (mod_id),
    CONSTRAINT fk_workshop_comments_raw_batch
        FOREIGN KEY (batch_id) REFERENCES crawl_batches(batch_id)
);

CREATE TABLE IF NOT EXISTS steam_api_mods_raw (
    batch_id VARCHAR(64) NOT NULL,
    mod_id BIGINT NOT NULL,
    api_page INT NULL,
    title VARCHAR(500) NULL,
    creator BIGINT NULL,
    consumer_appid INT NULL,
    time_created_epoch BIGINT NULL,
    time_created_utc DATETIME NULL,
    time_updated_epoch BIGINT NULL,
    time_updated_utc DATETIME NULL,
    subscriptions BIGINT NULL,
    favorited BIGINT NULL,
    lifetime_subscriptions BIGINT NULL,
    lifetime_favorited BIGINT NULL,
    views BIGINT NULL,
    num_comments_public BIGINT NULL,
    votes_up BIGINT NULL,
    votes_down BIGINT NULL,
    score DECIMAL(12,10) NULL,
    file_size BIGINT NULL,
    preview_url TEXT NULL,
    file_url TEXT NULL,
    short_description LONGTEXT NULL,
    tags_json LONGTEXT NULL,
    crawl_time_utc DATETIME NOT NULL,
    PRIMARY KEY (batch_id, mod_id),
    INDEX idx_steam_api_mods_raw_mod_id (mod_id)
);
