import { useDeferredValue, useEffect, useMemo, useState } from 'react';
import { CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import Panel from '../components/Panel';
import StatCard from '../components/StatCard';
import TagPill from '../components/TagPill';
import { getQuadrantMeta, quadrantMeta } from '../lib/constants';
import { loadDimTags, loadMods } from '../lib/data';
import { formatCompact, formatDays, formatNumber } from '../lib/format';

const maxPoints = 3200;

function ActivityTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  return (
    <div className="rounded-dst border border-dst-gold bg-dst-dark p-3 font-hans text-sm text-dst-text">
      <div className="font-title font-semibold text-dst-text-title">{item.title}</div>
      <div className="mt-2">订阅量：{formatNumber(item.subscriptions)}</div>
      <div>维护时长：{formatDays(item.maintenanceDays)}</div>
      <div>距今更新：{formatDays(item.daysSinceLastUpdate)}</div>
      <div className="mt-2 text-dst-text-dim">{getQuadrantMeta(item.quadrant).label}</div>
    </div>
  );
}

function buildScatterPoints(mods) {
  const toPoint = (mod) => ({ id: mod.id, title: mod.title, quadrant: mod.quadrant, maintenanceDays: mod.maintenanceDays, daysSinceLastUpdate: mod.daysSinceLastUpdate, subscriptions: mod.subscriptions, x: mod.maintenanceDays, y: Math.log10(mod.subscriptions + 1) });
  if (mods.length <= maxPoints) return { sampled: false, items: mods.map(toPoint) };
  const keepTop = Math.min(400, mods.length);
  const remaining = mods.slice(keepTop);
  const remainingBudget = Math.max(1, maxPoints - keepTop);
  const step = Math.ceil(remaining.length / remainingBudget);
  const sampled = mods.slice(0, keepTop).concat(remaining.filter((_, index) => index % step === 0).slice(0, remainingBudget));
  return { sampled: true, items: sampled.map(toPoint) };
}

export default function ActivityPage() {
  const [state, setState] = useState({ loading: true, error: null, mods: null, dimTags: null });
  const [query, setQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState('全部');
  const [selectedQuadrant, setSelectedQuadrant] = useState('全部');
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());

  useEffect(() => {
    let active = true;
    Promise.all([loadMods(), loadDimTags()])
      .then(([mods, dimTags]) => { if (active) setState({ loading: false, error: null, mods, dimTags }); })
      .catch((error) => { if (active) setState({ loading: false, error, mods: null, dimTags: null }); });
    return () => { active = false; };
  }, []);

  const filteredMods = useMemo(() => {
    if (!state.mods) return [];
    let next = state.mods.items;
    if (deferredQuery) next = next.filter((mod) => mod.searchKey.includes(deferredQuery) || mod.id.includes(deferredQuery));
    if (selectedTag !== '全部') next = next.filter((mod) => mod.tags.includes(selectedTag));
    if (selectedQuadrant !== '全部') next = next.filter((mod) => mod.quadrant === selectedQuadrant);
    return next;
  }, [state.mods, deferredQuery, selectedTag, selectedQuadrant]);

  const summary = useMemo(() => Object.keys(quadrantMeta).map((key) => {
    const mods = filteredMods.filter((item) => item.quadrant === key);
    const avgSubscriptions = mods.length ? mods.reduce((sum, item) => sum + item.subscriptions, 0) / mods.length : 0;
    const avgDaysSinceUpdate = mods.length ? mods.reduce((sum, item) => sum + item.daysSinceLastUpdate, 0) / mods.length : 0;
    return { key, meta: getQuadrantMeta(key), count: mods.length, avgSubscriptions, avgDaysSinceUpdate };
  }), [filteredMods]);
  const scatterState = useMemo(() => buildScatterPoints(filteredMods), [filteredMods]);
  const grouped = Object.keys(quadrantMeta).map((key) => ({ key, meta: getQuadrantMeta(key), data: scatterState.items.filter((item) => item.quadrant === key) }));
  const thresholds = { subscriptionMedian: state.mods?.items[0]?.subscriptionMedian ?? 232, maintenanceMedian: state.mods?.items[0]?.maintenanceMedian ?? 1 };

  if (state.loading) return <LoadingState label="正在加载活跃度四象限…" />;
  if (state.error) return <EmptyState title="活跃度数据加载失败" description={state.error.message} />;

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Activity" title="活跃度四象限" description="横轴是维护时长，纵轴是订阅量。因为点位接近全量，散点图会在命中过多时自动降级为抽样展示，同时保留四象限统计卡片。" />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summary.map((item) => (
          <StatCard key={item.key} label={item.meta.label} value={formatNumber(item.count)} hint={`平均订阅 ${formatCompact(item.avgSubscriptions)} · 平均距今更新 ${formatDays(item.avgDaysSinceUpdate)}`} />
        ))}
      </div>

      <Panel title="筛选条件" subtitle="散点点数过多时，会保留头部作品并对剩余样本等距抽样。">
        <div className="grid gap-4 lg:grid-cols-[2fr_1fr_1fr]">
          <label><div className="mb-2 font-hans text-sm text-dst-text-dim">搜索 Mod 名称或 ID</div><input className="input-dark" onChange={(event) => setQuery(event.target.value)} placeholder="例如 Health / 375859599" value={query} /></label>
          <label><div className="mb-2 font-hans text-sm text-dst-text-dim">标签</div><select className="input-dark" onChange={(event) => setSelectedTag(event.target.value)} value={selectedTag}><option value="全部">全部标签</option>{state.dimTags.items.slice(0, 20).map((tag) => <option key={tag.tag} value={tag.tag}>{tag.tag}</option>)}</select></label>
          <label><div className="mb-2 font-hans text-sm text-dst-text-dim">四象限</div><select className="input-dark" onChange={(event) => setSelectedQuadrant(event.target.value)} value={selectedQuadrant}><option value="全部">全部象限</option>{Object.entries(quadrantMeta).map(([key, meta]) => <option key={key} value={key}>{meta.label}</option>)}</select></label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 font-hans text-sm text-dst-text-dim">
          <span>当前命中 {formatNumber(filteredMods.length)} 个 Mod</span>
          {selectedTag !== '全部' ? <TagPill>{selectedTag}</TagPill> : null}
          {selectedQuadrant !== '全部' ? <TagPill>{getQuadrantMeta(selectedQuadrant).label}</TagPill> : null}
          {scatterState.sampled
            ? <TagPill className="border-[#c75b39]/30 bg-[#c75b39]/10 text-[#c75b39]">已自动抽样到 {formatNumber(scatterState.items.length)} 点</TagPill>
            : <TagPill className="border-[#7db862]/30 bg-[#7db862]/10 text-[#7db862]">当前未抽样</TagPill>
          }
        </div>
      </Panel>

      <Panel title="四象限散点图" subtitle="纵轴做了 log10 变换，避免极高订阅作品把其他点全部压扁。">
        <div className="h-[540px]">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 16, right: 24, bottom: 18, left: 8 }}>
              <CartesianGrid stroke="rgba(232, 184, 75, 0.06)" strokeDasharray="3 3" />
              <ReferenceLine stroke="#e8b84b" strokeDasharray="5 5" strokeOpacity={0.4} x={thresholds.maintenanceMedian} />
              <ReferenceLine stroke="#e8b84b" strokeDasharray="5 5" strokeOpacity={0.4} y={Math.log10(thresholds.subscriptionMedian + 1)} />
              <XAxis dataKey="x" stroke="#5c4a3a" tick={{ fill: '#a89880', fontSize: 12 }} type="number" />
              <YAxis dataKey="y" stroke="#5c4a3a" tick={{ fill: '#a89880', fontSize: 12 }} tickFormatter={(value) => formatCompact(Math.round(10 ** value - 1))} type="number" />
              <Tooltip content={<ActivityTooltip />} cursor={{ strokeDasharray: '4 4' }} />
              {grouped.map((group) => (
                <Scatter key={group.key} data={group.data} fill={group.meta.color} name={group.meta.label}>
                  {group.data.map((item) => <Cell key={`${group.key}-${item.id}`} fill={group.meta.color} stroke="#1a1410" strokeWidth={1} />)}
                </Scatter>
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </Panel>
    </div>
  );
}
