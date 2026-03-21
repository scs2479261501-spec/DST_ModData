# 指标定义

## 模块一：四象限活跃度分析

数据来源：
- 表：`steam_api_mods_raw`
- 使用最新一批 API 全量数据

分类覆盖范围：
- 只有同时具备 `subscriptions`、`time_created_utc`、`time_updated_utc` 的 mod 才参与四象限分类。
- 在 2026-03-19 这批全量数据中，可分类 mod 为 `22,919` 个，另有 `1` 条原始记录因关键字段为空被排除。

核心指标：
- `maintenance_days`
  - 定义：`DATEDIFF(time_updated_utc, time_created_utc)`
  - 含义：mod 从创建到最后一次更新之间的维护跨度，不代表更新次数。
- `days_since_last_update`
  - 定义：`DATEDIFF(CURDATE(), time_updated_utc)`
  - 含义：距离今天的天数，用于区分“历史维护跨度长”和“最近仍在维护”。
- `subscription_median`
  - 定义：最新批次中，`subscriptions` 的中位数
  - 当前值：`232`
- `maintenance_median`
  - 定义：最新批次中，`maintenance_days` 的中位数
  - 当前值：`1`

四象限分桶规则：
- 高订阅：`subscriptions > subscription_median`
- 低订阅：`subscriptions <= subscription_median`
- 高维护：`maintenance_days > maintenance_median`
- 低维护：`maintenance_days <= maintenance_median`

四象限标签：
- `evergreen`
  - 中文：`常青树`
  - 规则：高订阅 + 高维护
- `hit_then_abandoned`
  - 中文：`爆款弃坑`
  - 规则：高订阅 + 低维护
- `passion_project`
  - 中文：`用爱发电`
  - 规则：低订阅 + 高维护
- `silent_fade`
  - 中文：`沉默消亡`
  - 规则：低订阅 + 低维护

## 模块二：标签供需矩阵

数据来源：
- 表：`steam_api_mods_raw`
- 使用最新一批 API 全量数据

标签标准化规则：
- 从 `tags_json` 中展开标签数组
- 对标签值做 `LOWER(TRIM(tag))` 标准化
- 按 `(mod_id, tag)` 去重，避免同一 mod 重复计入同一标签
- 排除 `version:%` 和 `version_compatible:%` 这类版本标签

核心指标：
- `mod_count`
  - 定义：某标签下的 distinct mod 数量
  - 含义：该标签的供给规模
- `avg_subscriptions`
  - 定义：某标签下 `subscriptions` 的均值
  - 含义：需求均值参考，但容易被头部爆款抬高
- `median_subscriptions`
  - 定义：某标签下 `subscriptions` 的中位数
  - 含义：供需矩阵里的主需求轴，比均值更稳健
- `p75_subscriptions`
  - 定义：某标签下 `subscriptions` 的离散 P75
  - 含义：该标签中上游作品的需求上限参考

稳定标签规则：
- 只有 `mod_count >= 100` 的标签参与“蓝海 / 红海 / 拥挤强势 / 冷门弱势”分类
- 当前批次满足这个条件的标签有 `19` 个

模块二阈值：
- `supply_median_threshold = 1466`
- `demand_median_threshold = 701.0`
- `p75_median_threshold = 4098`

市场分区规则：
- `blue_ocean`
  - 规则：`mod_count < supply_median_threshold` 且 `median_subscriptions > demand_median_threshold`
  - 含义：供给偏少，但需求偏高
- `red_ocean`
  - 规则：`mod_count > supply_median_threshold` 且 `median_subscriptions < demand_median_threshold`
  - 含义：供给偏多，但需求偏弱
- `crowded_but_strong`
  - 规则：`mod_count > supply_median_threshold` 且 `median_subscriptions > demand_median_threshold`
  - 含义：赛道拥挤，但需求仍然健康
- `cold_niche`
  - 规则：其余稳定标签，包括等于阈值的边界情况
  - 含义：供给不多，但需求没有明显高于市场中位线，或者正好落在边界上

低样本标签处理：
- `mod_count < 100` 的标签标记为 `low_sample`
- 这类标签可以保留在原始分析表中，但不进入正式商业结论

## 模块三：作者生产力分析

数据来源：
- 表：`steam_api_mods_raw`
- 使用最新一批 API 全量数据
- 作者主键使用 API 返回的 `creator` 字段，即 Steam creator ID

作者级指标：
- `mod_count`
  - 定义：作者名下 mod 数量
- `total_subscriptions`
  - 定义：作者名下全部 mod 的订阅量之和
  - 含义：作者总体影响力 / 总需求代理指标
- `avg_subscriptions`
  - 定义：作者名下 mod 的平均订阅量
  - 含义：作者平均单作表现
- `median_subscriptions`
  - 定义：作者名下 mod 订阅量中位数
  - 含义：比均值更稳健的作者单作表现指标
- `avg_positive_rate`
  - 定义：先按单个 mod 计算 `votes_up / (votes_up + votes_down)`，再对作者名下 mod 取平均
  - 含义：作者平均口碑水平
- `avg_maintenance_days`
  - 定义：作者名下 mod 的 `maintenance_days` 平均值
  - 含义：作者作品整体维护跨度
- `tag_breadth`
  - 定义：作者覆盖的去重标准化标签数
  - 含义：作者创作题材广度

头部集中度指标：
- `top_1pct_share_pct`
  - 定义：按 `total_subscriptions` 排序后，前 1% 作者占全部作者总订阅量的比例
- `top_10_share_pct`
  - 定义：按 `total_subscriptions` 排序后，前 10 名作者占全部作者总订阅量的比例

高产是否高质：
- 主检验口径：`mod_count` 与 `avg_subscriptions`、`avg_positive_rate` 的 Pearson 相关系数
- 辅助口径：按 `1`、`2_3`、`4_9`、`10_plus` 四档查看作者平均表现

缺失处理：
- `creator IS NULL` 的记录不进入作者分析
- 如果某个 mod 没有有效投票总数，则该 mod 的好评率记为 `NULL`，不参与作者平均好评率计算
- 标签广度沿用模块二的标签标准化规则：`LOWER(TRIM(tag))`，并排除版本标签

## 模块四：评论文本分析

数据来源：
- 公开 Workshop 评论页面
- 评论采集批次：`top500_comments_20260319`
- 最新 API 全量批次仅用于确定订阅排名，不直接提供评论文本

分组规则：
- 先按最新 API 批次中的 `subscriptions` 对 mod 做降序排名
- `top_100`
  - 规则：`subscription_rank <= 100`
- `rank_300_500`
  - 规则：`subscription_rank BETWEEN 300 AND 500`
- 当前模块只对这两组做文本差异对比，不使用 `rank_101_299`

采集规则：
- 从前 `500` 个 mod 中按 rank 逐个抓取公开评论页
- 每个 mod 最多抓前 `2` 页评论
- 当前批次共成功落盘 `17,782` 条评论
- 受 Steam `429` 限流影响，存在大量 mod 抓取失败，因此评论分析按“成功采到评论的样本”解释，而不是按理论上的前 500 全量解释

文本预处理规则：
- 使用正则 `r"[a-z][a-z0-9']+"` 做英文 token 提取
- 默认停用词会去掉常见虚词，以及 `mod`、`game`、`dst`、`steam` 等领域高频噪音词
- 同一条评论里同一个词重复出现时，只按 `1` 条评论命中计数，避免长评论重复刷高词频
- 纯非英文评论不会进入关键词差异统计

核心指标：
- `comment_count`
  - 定义：某组成功采到的评论总数
- `mod_count`
  - 定义：某组中实际有评论落盘的 distinct mod 数量
- `tokenized_comment_count`
  - 定义：某组中至少能提取出 `1` 个有效英文 token 的评论数
  - 含义：真正进入关键词比较的评论基数
- `comments_per_1000`
  - 定义：某关键词在某组中，命中的评论数 / 该组 `tokenized_comment_count` * 1000
  - 含义：标准化后的评论文档频率，用于消除两组样本量不一致的影响
- `comments_per_1000_diff`
  - 定义：`top_100_comments_per_1000 - rank_300_500_comments_per_1000`
  - 含义：关键词对哪一组更有区分力
- `rate_ratio`
  - 定义：`top_100_comments_per_1000 / rank_300_500_comments_per_1000`
  - 含义：差异强度参考，不作为唯一排序依据

筛词规则：
- 只有在两组合计至少命中 `20` 条可分词评论的关键词，才进入正式差异表
- 当前输出文件默认保留每组最有区分度的前 `30` 个关键词

解释边界：
- 该模块反映的是“评论区讨论主题差异”，不是严格情感分析
- `subscriptions` 只是 adoption 代理指标，因此 `top_100` 与 `rank_300_500` 的差异更适合解释为“头部 vs 中腰部 mod 的用户讨论差异”
- 如果评论区里大量出现 `bug`、`crash`、`lua`，不应直接解读为 mod 质量差，也可能说明该 mod 使用规模大、讨论活跃、承担了更多支持交流功能
