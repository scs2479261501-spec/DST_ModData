import { useEffect, useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import Panel from '../components/Panel';
import StatCard from '../components/StatCard';
import TagPill from '../components/TagPill';
import { commentGroupMeta } from '../lib/constants';
import { loadCommentKeywords } from '../lib/data';
import { formatNumber } from '../lib/format';

function KeywordTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  return (
    <div className="rounded-dst border border-dst-gold bg-dst-dark p-3 font-hans text-sm text-dst-text">
      <div className="font-title font-semibold text-dst-text-title">{item.token}</div>
      <div className="mt-2">Top 100 每千评论：{item.top100Per1000}</div>
      <div>第 300-500 名每千评论：{item.rank300500Per1000}</div>
      <div>差值：{item.diffPer1000}</div>
    </div>
  );
}

export default function CommentsPage() {
  const [state, setState] = useState({ loading: true, error: null, comments: null });

  useEffect(() => {
    let active = true;
    loadCommentKeywords().then((comments) => { if (active) setState({ loading: false, error: null, comments }); }).catch((error) => { if (active) setState({ loading: false, error, comments: null }); });
    return () => { active = false; };
  }, []);

  const top100Words = useMemo(() => {
    const items = state.comments?.items ?? [];
    return items.filter((item) => item.dominantGroup === 'top_100').sort((a, b) => b.diffPer1000 - a.diffPer1000).slice(0, 12).map((item) => ({ ...item, value: item.top100Per1000 }));
  }, [state.comments]);
  const rank300500Words = useMemo(() => {
    const items = state.comments?.items ?? [];
    return items.filter((item) => item.dominantGroup === 'rank_300_500').sort((a, b) => a.diffPer1000 - b.diffPer1000).slice(0, 12).map((item) => ({ ...item, value: item.rank300500Per1000 }));
  }, [state.comments]);

  if (state.loading) return <LoadingState label="正在加载评论关键词分析…" />;
  if (state.error) return <EmptyState title="评论分析数据加载失败" description={state.error.message} />;

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Comments" title="评论关键词差异" description="直接比较 Top 100 高订阅 Mod 与第 300-500 名 Mod 的评论差异。当前词频只统计可分词的英文评论。" />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {state.comments.groups.map((group, index) => (
          <StatCard key={group.group} label={commentGroupMeta[group.group] ?? group.label} value={`${formatNumber(group.modsWithComments)} / ${formatNumber(group.selected)}`} hint={`评论 ${formatNumber(group.comments)} 条 · 覆盖率 ${group.coverage}%`} />
        ))}
        <StatCard label="关键词样本数" value={formatNumber(state.comments.meta.rowCount)} hint="双组差异词总量" />
        <StatCard label="方法说明" value="英文词频" hint="不包含中文分词" />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="Top 100 优势词" subtitle="这些词在高订阅 Mod 评论里更常出现，偏向稳定性、兼容性和支持讨论。">
          <div className="h-[420px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={top100Words} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 12 }}>
                <CartesianGrid stroke="rgba(232, 184, 75, 0.06)" strokeDasharray="3 3" />
                <XAxis stroke="#5c4a3a" tick={{ fill: '#a89880', fontSize: 12 }} type="number" />
                <YAxis dataKey="token" stroke="#5c4a3a" tick={{ fill: '#e8dcc8', fontSize: 12 }} type="category" width={92} />
                <Tooltip content={<KeywordTooltip />} />
                <Bar dataKey="value" fill="#e8b84b" radius={[0, 2, 2, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="第 300-500 名优势词" subtitle="这些词在中腰部 Mod 评论里更常出现，偏向角色、机制和玩法体验。">
          <div className="h-[420px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rank300500Words} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 12 }}>
                <CartesianGrid stroke="rgba(232, 184, 75, 0.06)" strokeDasharray="3 3" />
                <XAxis stroke="#5c4a3a" tick={{ fill: '#a89880', fontSize: 12 }} type="number" />
                <YAxis dataKey="token" stroke="#5c4a3a" tick={{ fill: '#e8dcc8', fontSize: 12 }} type="category" width={92} />
                <Tooltip content={<KeywordTooltip />} />
                <Bar dataKey="value" fill="#7db862" radius={[0, 2, 2, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <Panel title="差异关键词总表" subtitle="差值为 Top 100 每千评论词频减去第 300-500 名每千评论词频。">
        <div className="mb-4 flex flex-wrap gap-2 font-hans text-sm text-dst-text-dim"><TagPill>仅统计英文 token</TagPill><TagPill>Top 100 评论更偏支持与排障</TagPill><TagPill>300-500 名更偏角色与玩法表达</TagPill></div>
        <div className="table-shell overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-dst-dark text-dst-gold" style={{ fontVariant: 'small-caps', letterSpacing: '0.05em' }}>
              <tr>
                <th className="px-4 py-4 font-title font-medium">关键词</th>
                <th className="px-4 py-4 font-title font-medium">优势组</th>
                <th className="px-4 py-4 font-title font-medium">Top 100 / 千条</th>
                <th className="px-4 py-4 font-title font-medium">300-500 / 千条</th>
                <th className="px-4 py-4 font-title font-medium">差值</th>
              </tr>
            </thead>
            <tbody>
              {state.comments.items.map((item) => (
                <tr key={`${item.token}-${item.dominantGroup}`} className="table-row-alt border-t border-dst-border/30 text-dst-text">
                  <td className="px-4 py-4 font-semibold text-dst-text-title">{item.token}</td>
                  <td className="px-4 py-4 font-hans">{commentGroupMeta[item.dominantGroup] ?? item.dominantGroup}</td>
                  <td className="px-4 py-4 font-mono">{item.top100Per1000}</td>
                  <td className="px-4 py-4 font-mono">{item.rank300500Per1000}</td>
                  <td className="px-4 py-4 font-mono">{item.diffPer1000}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
