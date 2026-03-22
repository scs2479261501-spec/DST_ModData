import { useDeferredValue, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import Panel from '../components/Panel';
import StatCard from '../components/StatCard';
import TagPill from '../components/TagPill';
import { concentrationBandMeta, productivityBucketMeta } from '../lib/constants';
import { loadAuthors, loadMods } from '../lib/data';
import { formatCompact, formatNumber, formatPercentValue, formatRate } from '../lib/format';

const pageSize = 40;

function CurveTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  return (
    <div className="rounded-dst border border-dst-gold bg-dst-dark p-3 font-hans text-sm text-dst-text">
      <div>作者排名：#{formatNumber(item.rank)}</div>
      <div className="mt-1">累计订阅占比：{formatPercentValue(item.share)}</div>
    </div>
  );
}

export default function AuthorsPage() {
  const [state, setState] = useState({ loading: true, error: null, authors: null, mods: null });
  const [query, setQuery] = useState('');
  const [bucket, setBucket] = useState('全部');
  const [band, setBand] = useState('全部');
  const [sortBy, setSortBy] = useState('rank');
  const [page, setPage] = useState(1);
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());

  useEffect(() => {
    let active = true;
    Promise.all([loadAuthors(), loadMods()])
      .then(([authors, mods]) => {
        if (active) setState({ loading: false, error: null, authors, mods });
      })
      .catch((error) => {
        if (active) setState({ loading: false, error, authors: null, mods: null });
      });
    return () => { active = false; };
  }, []);

  useEffect(() => { setPage(1); }, [deferredQuery, bucket, band, sortBy]);

  const modMap = useMemo(() => new Map((state.mods?.items ?? []).map((item) => [item.id, item])), [state.mods]);

  const filteredAuthors = useMemo(() => {
    if (!state.authors) return [];
    let next = state.authors.items;
    if (deferredQuery) {
      next = next.filter((author) => author.id.includes(deferredQuery) || author.mods.some((modId) => (modMap.get(modId)?.title ?? '').toLowerCase().includes(deferredQuery)));
    }
    if (bucket !== '全部') next = next.filter((author) => author.productivityBucket === bucket);
    if (band !== '全部') next = next.filter((author) => author.concentrationBand === band);
    const sorted = [...next];
    switch (sortBy) {
      case 'totalSubscriptions': sorted.sort((a, b) => b.totalSubscriptions - a.totalSubscriptions || a.rank - b.rank); break;
      case 'avgSubscriptions': sorted.sort((a, b) => b.avgSubscriptions - a.avgSubscriptions || a.rank - b.rank); break;
      case 'modCount': sorted.sort((a, b) => b.modCount - a.modCount || a.rank - b.rank); break;
      case 'positiveRate': sorted.sort((a, b) => b.avgPositiveRate - a.avgPositiveRate || a.rank - b.rank); break;
      default: sorted.sort((a, b) => a.rank - b.rank);
    }
    return sorted;
  }, [state.authors, deferredQuery, bucket, band, sortBy, modMap]);

  if (state.loading) return <LoadingState label="正在加载作者分析…" />;
  if (state.error) return <EmptyState title="作者数据加载失败" description={state.error.message} />;

  const authors = state.authors.items;
  const totalAuthors = authors.length;
  const top10Share = authors[Math.min(9, totalAuthors - 1)]?.cumulativeSharePct ?? 0;
  const top1Count = Math.max(1, Math.ceil(totalAuthors * 0.01));
  const top1Share = authors[top1Count - 1]?.cumulativeSharePct ?? 0;
  const maxModCount = authors.reduce((current, item) => Math.max(current, item.modCount), 0);
  const curveData = authors.filter((author, index) => index < 200 || index % 20 === 0 || index === authors.length - 1).map((author) => ({ rank: author.rank, share: author.cumulativeSharePct }));
  const totalPages = Math.max(1, Math.ceil(filteredAuthors.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pageItems = filteredAuthors.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Authors" title="作者排行与头部集中度" description="作者页同时回答两个问题：头部集中度到底有多高，以及高产作者是否真的更强。列表支持按生产力分层和集中度带宽筛选。" />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="作者总量" value={formatNumber(totalAuthors)} hint="来自作者聚合表" />
        <StatCard label="前 10 作者占比" value={formatPercentValue(top10Share)} hint="累计总订阅占比" />
        <StatCard label={`前 1%（${formatNumber(top1Count)} 人）占比`} value={formatPercentValue(top1Share)} hint="平台头部集中度" />
        <StatCard label="最高产作者作品数" value={formatNumber(maxModCount)} hint="作者产量上限" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel title="头部集中度曲线" subtitle="横轴是作者排名，纵轴是累计订阅占比。">
          <div className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={curveData} margin={{ top: 16, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="rgba(232, 184, 75, 0.06)" strokeDasharray="3 3" />
                <XAxis dataKey="rank" stroke="#5c4a3a" tick={{ fill: '#a89880', fontSize: 12 }} />
                <YAxis stroke="#5c4a3a" tick={{ fill: '#a89880', fontSize: 12 }} tickFormatter={(value) => `${Number(value).toFixed(0)}%`} />
                <Tooltip content={<CurveTooltip />} />
                <Line dataKey="share" dot={false} stroke="#e8b84b" strokeWidth={2.5} type="monotone" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="筛选与排序" subtitle="列表页默认按作者排名展示。">
          <div className="grid gap-4">
            <label><div className="mb-2 font-hans text-sm text-dst-text-dim">搜索作者 ID 或其作品名</div><input className="input-dark" onChange={(event) => setQuery(event.target.value)} placeholder="例如 76561198025931302 或 Combined" value={query} /></label>
            <label><div className="mb-2 font-hans text-sm text-dst-text-dim">生产力分层</div><select className="input-dark" onChange={(event) => setBucket(event.target.value)} value={bucket}><option value="全部">全部分层</option>{Object.entries(productivityBucketMeta).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
            <label><div className="mb-2 font-hans text-sm text-dst-text-dim">集中度带宽</div><select className="input-dark" onChange={(event) => setBand(event.target.value)} value={band}><option value="全部">全部带宽</option>{Object.entries(concentrationBandMeta).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
            <label><div className="mb-2 font-hans text-sm text-dst-text-dim">排序</div><select className="input-dark" onChange={(event) => setSortBy(event.target.value)} value={sortBy}><option value="rank">作者排名</option><option value="totalSubscriptions">总订阅</option><option value="avgSubscriptions">平均订阅</option><option value="modCount">作品数</option><option value="positiveRate">平均好评率</option></select></label>
            <div className="flex flex-wrap gap-2 pt-1 font-hans text-sm text-dst-text-dim"><span>命中 {formatNumber(filteredAuthors.length)} 位作者</span>{bucket !== '全部' ? <TagPill>{productivityBucketMeta[bucket]}</TagPill> : null}{band !== '全部' ? <TagPill>{concentrationBandMeta[band]}</TagPill> : null}</div>
          </div>
        </Panel>
      </div>

      <div className="table-shell overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-dst-dark text-dst-gold" style={{ fontVariant: 'small-caps', letterSpacing: '0.05em' }}>
            <tr>
              <th className="px-4 py-4 font-title font-medium">排名</th>
              <th className="px-4 py-4 font-title font-medium">作者</th>
              <th className="px-4 py-4 font-title font-medium">作品数</th>
              <th className="px-4 py-4 font-title font-medium">总订阅</th>
              <th className="px-4 py-4 font-title font-medium">平均订阅</th>
              <th className="px-4 py-4 font-title font-medium">平均好评率</th>
              <th className="px-4 py-4 font-title font-medium">带宽</th>
              <th className="px-4 py-4 font-title font-medium">代表作</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.map((author) => {
              const leadMod = author.mods.map((modId) => modMap.get(modId)).find(Boolean);
              return (
                <tr key={author.id} className="table-row-alt border-t border-dst-border/30 align-top text-dst-text">
                  <td className="px-4 py-4 font-mono text-dst-text-dim">#{author.rank}</td>
                  <td className="px-4 py-4">
                    <Link className="font-mono text-dst-text-title hover:text-dst-gold" to={`/author/${author.id}`}>{author.id}</Link>
                    <div className="mt-2 font-hans text-sm text-dst-text-dim">{productivityBucketMeta[author.productivityBucket]}</div>
                  </td>
                  <td className="px-4 py-4 font-mono">{formatNumber(author.modCount)}</td>
                  <td className="px-4 py-4 font-mono text-dst-gold">{formatCompact(author.totalSubscriptions)}</td>
                  <td className="px-4 py-4 font-mono">{formatCompact(author.avgSubscriptions)}</td>
                  <td className="px-4 py-4 font-mono">{formatRate(author.avgPositiveRate)}</td>
                  <td className="px-4 py-4"><TagPill>{concentrationBandMeta[author.concentrationBand] ?? author.concentrationBand}</TagPill></td>
                  <td className="px-4 py-4 font-hans text-dst-text-dim">{leadMod ? leadMod.title : '无可用作品标题'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="font-hans text-sm text-dst-text-dim">第 {formatNumber(currentPage)} / {formatNumber(totalPages)} 页，每页 {pageSize} 位作者</div>
        <div className="flex gap-3">
          <button className="rounded-dst border border-dst-border bg-dst-brown px-4 py-2 font-hans text-sm text-dst-text transition-colors duration-300 hover:border-dst-gold hover:text-dst-gold disabled:cursor-not-allowed disabled:opacity-40" disabled={currentPage <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))} type="button">上一页</button>
          <button className="rounded-dst border border-dst-border bg-dst-brown px-4 py-2 font-hans text-sm text-dst-text transition-colors duration-300 hover:border-dst-gold hover:text-dst-gold disabled:cursor-not-allowed disabled:opacity-40" disabled={currentPage >= totalPages} onClick={() => setPage((value) => Math.min(totalPages, value + 1))} type="button">下一页</button>
        </div>
      </div>
    </div>
  );
}
