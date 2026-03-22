import { useEffect, useMemo, useState } from 'react';
import { CartesianGrid, Cell, Legend, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import Panel from '../components/Panel';
import StatCard from '../components/StatCard';
import { getMarketZoneMeta, marketZoneMeta } from '../lib/constants';
import { loadSupplyDemandTags } from '../lib/data';
import { formatCompact, formatNumber } from '../lib/format';

function TooltipContent({ active, payload }) {
  if (!active || !payload?.length) return null;
  const tag = payload[0].payload;
  return (
    <div className="rounded-dst border border-dst-gold bg-dst-dark p-3 font-hans text-sm text-dst-text">
      <div className="font-title font-semibold text-dst-text-title">{tag.tag}</div>
      <div className="mt-2">Mod 数量：{formatNumber(tag.modCount)}</div>
      <div>中位订阅：{formatNumber(tag.medianSubscriptions)}</div>
      <div>P75 订阅：{formatNumber(tag.p75Subscriptions)}</div>
      <div className="mt-2 text-dst-text-dim">{getMarketZoneMeta(tag.marketZone).label}</div>
    </div>
  );
}

export default function SupplyDemandPage() {
  const [state, setState] = useState({ loading: true, error: null, tags: null });
  const [stableOnly, setStableOnly] = useState(true);
  const [selectedZone, setSelectedZone] = useState('全部');

  useEffect(() => {
    let active = true;
    loadSupplyDemandTags().then((tags) => { if (active) setState({ loading: false, error: null, tags }); }).catch((error) => { if (active) setState({ loading: false, error, tags: null }); });
    return () => { active = false; };
  }, []);

  const filteredTags = useMemo(() => {
    if (!state.tags) return [];
    let next = state.tags.items;
    if (stableOnly) next = next.filter((item) => item.isStableTag);
    if (selectedZone !== '全部') next = next.filter((item) => item.marketZone === selectedZone);
    return [...next].sort((a, b) => b.medianSubscriptions - a.medianSubscriptions || a.modCount - b.modCount);
  }, [state.tags, stableOnly, selectedZone]);

  if (state.loading) return <LoadingState label="正在加载标签供需矩阵…" />;
  if (state.error) return <EmptyState title="标签供需数据加载失败" description={state.error.message} />;

  const stableRows = state.tags.items.filter((item) => item.isStableTag);
  const thresholds = stableRows[0] ?? state.tags.items[0];
  const zoneCards = Object.entries(marketZoneMeta).map(([key, meta]) => ({ key, label: meta.label, count: stableRows.filter((item) => item.marketZone === key).length }));
  const grouped = Object.keys(marketZoneMeta).map((zoneKey) => ({ zoneKey, meta: getMarketZoneMeta(zoneKey), data: filteredTags.filter((item) => item.marketZone === zoneKey) }));

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Supply Demand" title="标签供需矩阵" description="横轴是标签下的 Mod 数量，纵轴是中位订阅量，用来区分蓝海、红海、拥挤但强势和冷门区。默认只看样本数足够稳定的标签。" />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {zoneCards.map((card) => (
          <StatCard key={card.key} label={card.label} value={formatNumber(card.count)} hint="稳定标签数量" />
        ))}
      </div>

      <Panel title="散点筛选" subtitle="散点图上悬浮即可查看单个标签的供需位置。">
        <div className="flex flex-wrap gap-3">
          <button className={`rounded-dst border px-4 py-2 font-hans text-sm transition-colors duration-300 ${stableOnly ? 'border-dst-gold bg-dst-gold text-dst-darkest' : 'border-dst-border text-dst-text hover:border-dst-gold hover:text-dst-gold'}`} onClick={() => setStableOnly((value) => !value)} type="button">{stableOnly ? '仅看稳定标签' : '包含低样本标签'}</button>
          <select className="input-dark max-w-xs" onChange={(event) => setSelectedZone(event.target.value)} value={selectedZone}><option value="全部">全部市场分区</option>{Object.entries(marketZoneMeta).map(([key, meta]) => <option key={key} value={key}>{meta.label}</option>)}</select>
          <div className="flex items-center font-hans text-sm text-dst-text-dim">当前显示 {formatNumber(filteredTags.length)} 个标签</div>
        </div>
      </Panel>

      <Panel title="标签散点图" subtitle="参考线来自稳定标签的供给与需求中位线。">
        <div className="h-[520px]">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 16, right: 24, bottom: 18, left: 8 }}>
              <CartesianGrid stroke="rgba(232, 184, 75, 0.06)" strokeDasharray="3 3" />
              <ReferenceLine stroke="#e8b84b" strokeDasharray="5 5" strokeOpacity={0.4} x={thresholds?.supplyThreshold ?? 0} />
              <ReferenceLine stroke="#e8b84b" strokeDasharray="5 5" strokeOpacity={0.4} y={thresholds?.demandThreshold ?? 0} />
              <XAxis dataKey="modCount" stroke="#5c4a3a" tick={{ fill: '#a89880', fontSize: 12 }} type="number" />
              <YAxis dataKey="medianSubscriptions" stroke="#5c4a3a" tick={{ fill: '#a89880', fontSize: 12 }} type="number" />
              <ZAxis dataKey="p75Subscriptions" range={[80, 320]} />
              <Tooltip content={<TooltipContent />} cursor={{ strokeDasharray: '4 4' }} />
              <Legend formatter={(value) => getMarketZoneMeta(value).label} />
              {grouped.map((group) => (
                <Scatter key={group.zoneKey} data={group.data} fill={group.meta.color} name={group.zoneKey}>
                  {group.data.map((item) => <Cell key={`${group.zoneKey}-${item.tag}`} fill={group.meta.color} stroke="#1a1410" strokeWidth={1} />)}
                </Scatter>
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <Panel title="标签清单" subtitle="中位订阅量比均值更稳，所以列表按中位订阅量倒序。">
        <div className="table-shell overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-dst-dark text-dst-gold" style={{ fontVariant: 'small-caps', letterSpacing: '0.05em' }}>
              <tr>
                <th className="px-4 py-4 font-title font-medium">标签</th>
                <th className="px-4 py-4 font-title font-medium">市场分区</th>
                <th className="px-4 py-4 font-title font-medium">Mod 数量</th>
                <th className="px-4 py-4 font-title font-medium">平均订阅</th>
                <th className="px-4 py-4 font-title font-medium">中位订阅</th>
                <th className="px-4 py-4 font-title font-medium">P75 订阅</th>
              </tr>
            </thead>
            <tbody>
              {filteredTags.map((item) => {
                const meta = getMarketZoneMeta(item.marketZone);
                return (
                  <tr key={item.tag} className="table-row-alt border-t border-dst-border/30 text-dst-text">
                    <td className="px-4 py-4 font-hans font-semibold text-dst-text-title">{item.tag}</td>
                    <td className="px-4 py-4"><span className={`inline-flex rounded-sm border px-3 py-1 text-xs ${meta.badgeClass}`}>{meta.label}</span></td>
                    <td className="px-4 py-4 font-mono">{formatNumber(item.modCount)}</td>
                    <td className="px-4 py-4 font-mono">{formatCompact(item.avgSubscriptions)}</td>
                    <td className="px-4 py-4 font-mono text-dst-gold">{formatNumber(item.medianSubscriptions)}</td>
                    <td className="px-4 py-4 font-mono">{formatNumber(item.p75Subscriptions)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
