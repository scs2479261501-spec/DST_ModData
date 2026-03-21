# PowerBI 数据口径说明

目录：`powerbi_20260319`
- 导出批次：`powerbi_20260319`
- API 来源批次：`api_full_20260319`
- 评论来源批次：`top500_comments_20260319`
- CSV 数量：`13`

说明：
- 本目录下的原始 CSV 不做注释列追加，以避免破坏 PowerBI 连接。
- 中文口径统一写在本文件和 `字段口径_中文.csv` 中。
- 除评论页外，其余数据默认来自最新 API 全量批次。

## activity_mod_tags.csv

- 页面：`活跃度页`
- 角色：`mod-标签桥表`
- 粒度：`每行一条 mod 与标签的对应关系`
- 说明：用于把标签筛选器连接到四象限散点图，一个 mod 可以对应多个标签。

| 字段 | 中文口径 | 说明 |
|------|----------|------|
| `mod_id` | mod ID | 对应 activity_mods.csv 里的 mod_id。 |
| `tag` | 标准化标签 | 对应 dim_tags.csv 里的 tag。 |

## activity_mods.csv

- 页面：`活跃度页`
- 角色：`四象限事实表`
- 粒度：`每行一个可参与四象限分类的 mod`
- 说明：仅保留同时具备订阅量、创建时间、更新时间的 mod，用于四象限散点图。

| 字段 | 中文口径 | 说明 |
|------|----------|------|
| `mod_id` | mod ID | Steam publishedfileid，mod 主键。 |
| `title` | mod 标题 | mod 名称。 |
| `creator_id` | 作者 Steam ID | API 返回的 creator 字段。 |
| `subscriptions` | 当前订阅量 | 当前订阅数，作为 adoption 代理指标。 |
| `votes_up` | 点赞数 | API 返回的 vote_data.votes_up。 |
| `votes_down` | 点踩数 | API 返回的 vote_data.votes_down。 |
| `score` | 综合评分 | Steam API 返回的 score。 |
| `positive_rate` | 好评率 | votes_up / (votes_up + votes_down)，无有效投票时为空。 |
| `time_created_utc` | 创建时间 UTC | mod 创建时间的 UTC 时间戳。 |
| `time_updated_utc` | 最后更新时间 UTC | mod 最后更新时间的 UTC 时间戳。 |
| `maintenance_days` | 维护时长 | DATEDIFF(time_updated_utc, time_created_utc)，表示从创建到最后更新跨越了多少天。 |
| `days_since_last_update` | 距今天数 | DATEDIFF(CURDATE(), time_updated_utc)，表示距最近一次更新已过去多少天。 |
| `subscription_median` | 订阅中位线 | 当前批次订阅量中位数，当前导出中为 232。 |
| `maintenance_median` | 维护时长中位线 | 当前批次维护时长中位数，当前导出中为 1。 |
| `quadrant` | 四象限编码 | evergreen / hit_then_abandoned / passion_project / silent_fade。 |
| `quadrant_label` | 四象限名称 | 四象限英文展示名，适合直接做图例。 |

## authors_bucket_summary.csv

- 页面：`作者页`
- 角色：`作者产量分层汇总表`
- 粒度：`每行一个产量分层`
- 说明：用于比较 1、2-3、4-9、10+ 四档作者的整体表现。

| 字段 | 中文口径 | 说明 |
|------|----------|------|
| `productivity_bucket` | 产量分层 | 1 / 2-3 / 4-9 / 10+。 |
| `author_count` | 作者数 | 该分层下的作者数量。 |
| `total_subscriptions` | 总订阅量 | 该分层作者的 total_subscriptions 合计。 |
| `avg_total_subscriptions` | 平均总订阅量 | 该分层作者平均总订阅量。 |
| `avg_avg_subscriptions` | 平均单作订阅 | 该分层作者的 avg_subscriptions 平均值。 |
| `avg_positive_rate` | 平均好评率 | 该分层作者的 avg_positive_rate 平均值。 |
| `avg_maintenance_days` | 平均维护时长 | 该分层作者的 avg_maintenance_days 平均值。 |

## authors_concentration_curve.csv

- 页面：`作者页`
- 角色：`作者集中度曲线表`
- 粒度：`每行一个作者，按 author_rank 排序`
- 说明：与 authors_productivity.csv 同粒度，但主要用于累计占比曲线。

| 字段 | 中文口径 | 说明 |
|------|----------|------|
| `creator_id` | 作者 Steam ID | 作者主键。 |
| `mod_count` | mod 数量 | 作者名下 mod 数量。 |
| `total_subscriptions` | 总订阅量 | 作者名下全部 mod 的订阅量之和。 |
| `avg_subscriptions` | 平均订阅量 | 作者单个 mod 的平均订阅表现。 |
| `median_subscriptions` | 中位订阅量 | 作者单个 mod 订阅量的中位数。 |
| `avg_positive_rate` | 平均好评率 | 作者名下 mod 的平均好评率。 |
| `avg_maintenance_days` | 平均维护时长 | 作者名下 mod 的平均维护跨度。 |
| `tag_breadth` | 标签覆盖广度 | 作者覆盖的去重标签数。 |
| `author_rank` | 作者排名 | 按 total_subscriptions 从高到低排序。 |
| `productivity_bucket` | 产量分层 | 1 / 2-3 / 4-9 / 10+。 |
| `share_of_total_subscriptions_pct` | 总订阅占比 | 该作者占整体作者总订阅量的比例。 |
| `cumulative_subscriptions` | 累计总订阅 | 按排名累加到当前作者的总订阅量。 |
| `cumulative_share_pct` | 累计订阅占比 | 按排名累加到当前作者的总订阅占比。 |
| `concentration_band` | 集中度区间 | top_10 / top_1pct_other / others。 |

## authors_concentration_summary.csv

- 页面：`作者页`
- 角色：`作者集中度汇总表`
- 粒度：`单行汇总`
- 说明：用于作者集中度 KPI 卡片和核心结论展示。

| 字段 | 中文口径 | 说明 |
|------|----------|------|
| `author_count` | 作者总数 | 纳入作者分析的作者数量。 |
| `total_subscriptions_all` | 作者总订阅量 | 全部作者 total_subscriptions 之和。 |
| `top_1pct_author_count` | 前1%作者人数 | ceil(author_count * 1%)。 |
| `top_1pct_subscriptions` | 前1%作者总订阅 | 前 1% 作者贡献的总订阅量。 |
| `top_1pct_share_pct` | 前1%占比 | 前 1% 作者占全部作者总订阅量的比例。 |
| `top_10_subscriptions` | 前10作者总订阅 | 前 10 名作者贡献的总订阅量。 |
| `top_10_share_pct` | 前10占比 | 前 10 名作者占全部作者总订阅量的比例。 |

## authors_productivity.csv

- 页面：`作者页`
- 角色：`作者生产力主表`
- 粒度：`每行一个作者`
- 说明：用于作者排名、生产力分层、集中度明细等可视化。

| 字段 | 中文口径 | 说明 |
|------|----------|------|
| `creator_id` | 作者 Steam ID | 作者主键。 |
| `mod_count` | mod 数量 | 作者名下 mod 数量。 |
| `total_subscriptions` | 总订阅量 | 作者名下全部 mod 的订阅量之和。 |
| `avg_subscriptions` | 平均订阅量 | 作者单个 mod 的平均订阅表现。 |
| `median_subscriptions` | 中位订阅量 | 作者单个 mod 订阅量的中位数。 |
| `avg_positive_rate` | 平均好评率 | 作者名下 mod 的平均好评率。 |
| `avg_maintenance_days` | 平均维护时长 | 作者名下 mod 的平均维护跨度。 |
| `tag_breadth` | 标签覆盖广度 | 作者覆盖的去重标签数。 |
| `author_rank` | 作者排名 | 按 total_subscriptions 从高到低排序。 |
| `productivity_bucket` | 产量分层 | 1 / 2-3 / 4-9 / 10+。 |
| `share_of_total_subscriptions_pct` | 总订阅占比 | 该作者占整体作者总订阅量的比例。 |
| `cumulative_subscriptions` | 累计总订阅 | 按排名累加到当前作者的总订阅量。 |
| `cumulative_share_pct` | 累计订阅占比 | 按排名累加到当前作者的总订阅占比。 |
| `concentration_band` | 集中度区间 | top_10 / top_1pct_other / others。 |

## authors_top_20.csv

- 页面：`作者页`
- 角色：`作者 Top20 表`
- 粒度：`每行一个作者`
- 说明：从 authors_productivity.csv 中截取的前 20 名作者，适合直接做排行榜表格。

| 字段 | 中文口径 | 说明 |
|------|----------|------|
| `creator_id` | 作者 Steam ID | 作者主键。 |
| `mod_count` | mod 数量 | 作者名下 mod 数量。 |
| `total_subscriptions` | 总订阅量 | 作者名下全部 mod 的订阅量之和。 |
| `avg_subscriptions` | 平均订阅量 | 作者单个 mod 的平均订阅表现。 |
| `median_subscriptions` | 中位订阅量 | 作者单个 mod 订阅量的中位数。 |
| `avg_positive_rate` | 平均好评率 | 作者名下 mod 的平均好评率。 |
| `avg_maintenance_days` | 平均维护时长 | 作者名下 mod 的平均维护跨度。 |
| `tag_breadth` | 标签覆盖广度 | 作者覆盖的去重标签数。 |
| `author_rank` | 作者排名 | 按 total_subscriptions 从高到低排序。 |
| `productivity_bucket` | 产量分层 | 1 / 2-3 / 4-9 / 10+。 |
| `share_of_total_subscriptions_pct` | 总订阅占比 | 该作者占整体作者总订阅量的比例。 |
| `cumulative_subscriptions` | 累计总订阅 | 按排名累加到当前作者的总订阅量。 |
| `cumulative_share_pct` | 累计订阅占比 | 按排名累加到当前作者的总订阅占比。 |
| `concentration_band` | 集中度区间 | top_10 / top_1pct_other / others。 |

## comments_group_summary.csv

- 页面：`评论页`
- 角色：`评论样本覆盖汇总表`
- 粒度：`每行一个评论对比组`
- 说明：用于展示 Top 100 与 300-500 名两组评论样本的覆盖率和可分词规模。

| 字段 | 中文口径 | 说明 |
|------|----------|------|
| `rank_group` | 分组编码 | top_100 或 rank_300_500。 |
| `group_label` | 分组名称 | Top 100 或 Rank 300-500。 |
| `selected_mod_count` | 原计划 mod 数 | 按订阅排名落入该组的 mod 数。 |
| `mods_with_comments` | 有评论样本的 mod 数 | 成功抓到至少一条评论的 mod 数。 |
| `comment_count` | 评论总数 | 成功落盘的评论总数。 |
| `tokenized_comment_count` | 可分词评论数 | 至少能提取到一个英文 token 的评论数。 |
| `mod_coverage_pct` | mod 覆盖率 | mods_with_comments / selected_mod_count * 100。 |
| `tokenized_comment_share_pct` | 可分词占比 | tokenized_comment_count / comment_count * 100。 |
| `avg_comments_per_collected_mod` | 每个成功 mod 平均评论数 | comment_count / mods_with_comments。 |

## comments_keyword_comparison.csv

- 页面：`评论页`
- 角色：`评论关键词差异全量表`
- 粒度：`每行一个关键词`
- 说明：基于英文可分词评论的文档频率差异表，用于比较 Top 100 与 300-500 名两组评论主题。

| 字段 | 中文口径 | 说明 |
|------|----------|------|
| `token` | 关键词 | 英文分词后的关键词。 |
| `top_100_comment_count` | Top 100 命中评论数 | 在 Top 100 组中，包含该词的评论条数。 |
| `rank_300_500_comment_count` | 300-500 命中评论数 | 在 Rank 300-500 组中，包含该词的评论条数。 |
| `top_100_comments_per_1000` | Top 100 每千评论命中数 | Top 100 组的标准化文档频率。 |
| `rank_300_500_comments_per_1000` | 300-500 每千评论命中数 | Rank 300-500 组的标准化文档频率。 |
| `comments_per_1000_diff` | 每千评论差值 | top_100_comments_per_1000 - rank_300_500_comments_per_1000。 |
| `rate_ratio` | 频率比值 | top_100_comments_per_1000 / rank_300_500_comments_per_1000，右组为 0 时可能为空。 |
| `dominant_group` | 优势组 | 该词更偏向 top_100 还是 rank_300_500。 |

## comments_top_keywords.csv

- 页面：`评论页`
- 角色：`评论关键词展示表`
- 粒度：`每行一个关键词`
- 说明：从全量关键词差异表中各取每组最有区分度的前 20 个关键词，适合直接做条形图。

| 字段 | 中文口径 | 说明 |
|------|----------|------|
| `token` | 关键词 | 英文分词后的关键词。 |
| `dominant_group` | 优势组 | 该词更偏向 top_100 还是 rank_300_500。 |
| `top_100_comment_count` | Top 100 命中评论数 | 在 Top 100 组中，包含该词的评论条数。 |
| `rank_300_500_comment_count` | 300-500 命中评论数 | 在 Rank 300-500 组中，包含该词的评论条数。 |
| `top_100_comments_per_1000` | Top 100 每千评论命中数 | Top 100 组的标准化文档频率。 |
| `rank_300_500_comments_per_1000` | 300-500 每千评论命中数 | Rank 300-500 组的标准化文档频率。 |
| `comments_per_1000_diff` | 每千评论差值 | top_100_comments_per_1000 - rank_300_500_comments_per_1000。 |
| `rate_ratio` | 频率比值 | top_100_comments_per_1000 / rank_300_500_comments_per_1000。 |

## dim_tags.csv

- 页面：`概览页 / 活跃度页 / 供需页`
- 角色：`标签维表`
- 粒度：`每行一个标准化标签`
- 说明：作为标签词云和标签筛选器的公共维表，标签已统一转小写并去掉版本标签。

| 字段 | 中文口径 | 说明 |
|------|----------|------|
| `tag` | 标准化标签 | 标签名称，已做 lower(trim) 标准化，并排除 version:* 标签。 |
| `mod_count` | 标签下 mod 数 | 带有该标签的 distinct mod 数量，可用于词云大小和筛选热度。 |
| `avg_subscriptions` | 标签平均订阅 | 该标签下 mod 的订阅均值，容易受爆款影响，适合作为辅助参考。 |
| `tag_rank_by_mod_count` | 标签热度排名 | 按 mod_count 从高到低排序后的排名。 |
| `wordcloud_weight` | 词云权重 | 词云建议使用的权重字段，当前口径与 mod_count 相同。 |

## overview_kpis.csv

- 页面：`概览页`
- 角色：`KPI卡片数据`
- 粒度：`每行一个指标`
- 说明：用于概览页卡片，展示 mod 总量、作者总量、总订阅量。

| 字段 | 中文口径 | 说明 |
|------|----------|------|
| `metric_key` | 指标编码 | 指标的程序化键值，用于区分 mod_count、author_count、total_subscriptions。 |
| `metric_label` | 指标英文标签 | 给 PowerBI 可视化或字段面板使用的英文标签。 |
| `metric_value` | 指标原始值 | 可计算的数值字段，建议卡片图和度量引用此列。 |
| `display_value` | 展示文本 | 已经格式化好的展示文本，带千分位，适合直接做卡片显示。 |
| `sort_order` | 排序序号 | 控制 KPI 卡片在页面上的显示顺序。 |

## supply_demand_tags.csv

- 页面：`供需页`
- 角色：`标签供需矩阵事实表`
- 粒度：`每行一个标签`
- 说明：用于标签供需散点图，主轴是标签供给量和标签内订阅中位数。

| 字段 | 中文口径 | 说明 |
|------|----------|------|
| `tag` | 标准化标签 | 标签名称，已标准化。 |
| `mod_count` | 标签供给量 | 该标签下的 distinct mod 数量。 |
| `avg_subscriptions` | 平均订阅 | 该标签下 mod 的订阅均值。 |
| `median_subscriptions` | 中位订阅 | 该标签下 mod 的订阅中位数，是供需图的主需求轴。 |
| `p75_subscriptions` | P75订阅 | 该标签下订阅的离散 P75，用于反映中上游表现。 |
| `is_stable_tag` | 稳定标签标记 | 1 表示 mod_count >= 100，属于正式商业分析标签。 |
| `supply_median_threshold` | 供给中位线 | 标签层面的 mod_count 中位阈值。 |
| `demand_median_threshold` | 需求中位线 | 标签层面的 median_subscriptions 中位阈值。 |
| `p75_median_threshold` | P75中位线 | 标签层面的 p75_subscriptions 中位阈值。 |
| `supply_side` | 供给侧分类 | low_supply 或 high_supply。 |
| `demand_side` | 需求侧分类 | low_demand 或 high_demand。 |
| `market_zone` | 市场分区 | blue_ocean / red_ocean / crowded_but_strong / cold_niche / low_sample。 |
