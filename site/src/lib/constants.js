export const metricLabels = {
  mod_count: 'Mod 总量',
  author_count: '作者总量',
  total_subscriptions: '总订阅量',
  subscription_median: '订阅量中位数',
  maintenance_median: '维护天数中位数',
};

export const quadrantMeta = {
  evergreen: {
    label: '常青树',
    description: '高订阅 / 长维护',
    color: '#7db862',
    badgeClass: 'border-[#7db862]/30 bg-[#7db862]/10 text-[#7db862]',
  },
  hit_then_abandoned: {
    label: '爆款弃坑',
    description: '高订阅 / 短维护',
    color: '#e8b84b',
    badgeClass: 'border-[#e8b84b]/30 bg-[#e8b84b]/10 text-[#e8b84b]',
  },
  passion_project: {
    label: '用爱发电',
    description: '低订阅 / 长维护',
    color: '#9b7ec8',
    badgeClass: 'border-[#9b7ec8]/30 bg-[#9b7ec8]/10 text-[#9b7ec8]',
  },
  silent_fade: {
    label: '沉默消亡',
    description: '低订阅 / 短维护',
    color: '#8a7060',
    badgeClass: 'border-[#8a7060]/30 bg-[#8a7060]/10 text-[#8a7060]',
  },
};

export const marketZoneMeta = {
  blue_ocean: {
    label: '蓝海',
    color: '#5b9bd5',
    badgeClass: 'border-[#5b9bd5]/30 bg-[#5b9bd5]/10 text-[#5b9bd5]',
  },
  crowded_but_strong: {
    label: '拥挤但强势',
    color: '#e8b84b',
    badgeClass: 'border-[#e8b84b]/30 bg-[#e8b84b]/10 text-[#e8b84b]',
  },
  red_ocean: {
    label: '红海',
    color: '#c75b39',
    badgeClass: 'border-[#c75b39]/30 bg-[#c75b39]/10 text-[#c75b39]',
  },
  cold_niche: {
    label: '冷门区',
    color: '#9b7ec8',
    badgeClass: 'border-[#9b7ec8]/30 bg-[#9b7ec8]/10 text-[#9b7ec8]',
  },
  low_sample: {
    label: '低样本',
    color: '#8a7060',
    badgeClass: 'border-[#8a7060]/30 bg-[#8a7060]/10 text-[#8a7060]',
  },
};

export const productivityBucketMeta = {
  '1': '单 Mod 作者',
  '2-3': '2-3 个 Mod',
  '4-9': '4-9 个 Mod',
  '10+': '10 个及以上',
};

export const concentrationBandMeta = {
  top_10: '前 10 作者',
  top_1pct_other: '前 1% 其余作者',
  others: '其余作者',
};

export const commentGroupMeta = {
  top_100: 'Top 100 高订阅 Mod',
  rank_300_500: '第 300-500 名 Mod',
};

export function getQuadrantMeta(key) {
  return quadrantMeta[key] ?? {
    label: key,
    description: '未定义分组',
    color: '#8a7060',
    badgeClass: 'border-[#8a7060]/30 bg-[#8a7060]/10 text-[#8a7060]',
  };
}

export function getMarketZoneMeta(key) {
  return marketZoneMeta[key] ?? {
    label: key,
    color: '#8a7060',
    badgeClass: 'border-[#8a7060]/30 bg-[#8a7060]/10 text-[#8a7060]',
  };
}
