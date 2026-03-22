import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import Panel from '../components/Panel';
import StatCard from '../components/StatCard';
import TagPill from '../components/TagPill';
import { concentrationBandMeta, productivityBucketMeta } from '../lib/constants';
import { loadAuthors, loadMods } from '../lib/data';
import { formatCompact, formatDays, formatNumber, formatPercentValue, formatRate } from '../lib/format';

export default function AuthorDetailPage() {
  const { authorId } = useParams();
  const [state, setState] = useState({ loading: true, error: null, authors: null, mods: null });

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

  const author = useMemo(() => state.authors?.items.find((item) => item.id === authorId) ?? null, [state.authors, authorId]);
  const modMap = useMemo(() => new Map((state.mods?.items ?? []).map((item) => [item.id, item])), [state.mods]);
  const authorMods = useMemo(() => {
    if (!author) return [];
    return author.mods.map((modId) => modMap.get(modId)).filter(Boolean).sort((a, b) => b.subscriptions - a.subscriptions);
  }, [author, modMap]);
  const tagStats = useMemo(() => {
    const counter = new Map();
    authorMods.forEach((mod) => mod.tags.forEach((tag) => counter.set(tag, (counter.get(tag) ?? 0) + 1)));
    return [...counter.entries()].map(([tag, count]) => ({ tag, count })).sort((a, b) => b.count - a.count).slice(0, 12);
  }, [authorMods]);

  if (state.loading) return <LoadingState label="正在加载作者详情…" />;
  if (state.error) return <EmptyState title="作者详情加载失败" description={state.error.message} />;
  if (!author) return <EmptyState title="没有找到对应作者" description="这个作者 ID 不在当前站点的数据批次里。" action={<Link className="rounded-dst border border-dst-border bg-dst-brown px-4 py-2 font-hans text-sm text-dst-text hover:border-dst-gold hover:text-dst-gold" to="/authors">返回作者页</Link>} />;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow={`Author #${author.rank}`}
        title={`作者 ${author.id}`}
        description="作者详情页聚焦产量、总订阅、平均表现、标签覆盖和作品列表，用来判断这个作者到底是高产高质、单爆款，还是长尾贡献者。"
        actions={<Link className="rounded-dst border border-dst-border bg-dst-brown px-4 py-2 font-hans text-sm text-dst-text hover:border-dst-gold hover:text-dst-gold" to="/authors">返回作者页</Link>}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="作品数" value={formatNumber(author.modCount)} hint={productivityBucketMeta[author.productivityBucket]} />
        <StatCard label="总订阅" value={formatCompact(author.totalSubscriptions)} hint={`排名 #${author.rank}`} />
        <StatCard label="平均订阅" value={formatCompact(author.avgSubscriptions)} hint={`中位订阅 ${formatCompact(author.medianSubscriptions)}`} />
        <StatCard label="平均好评率" value={formatRate(author.avgPositiveRate)} hint={`平均维护 ${formatDays(author.avgMaintenanceDays)}`} />
        <StatCard label="标签覆盖广度" value={formatNumber(author.tagBreadth)} hint={`占总订阅 ${formatPercentValue(author.sharePct)}`} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <Panel title="作者画像" subtitle="这里保留作者分析模块最核心的解释性字段。">
          <div className="space-y-4 font-hans text-sm text-dst-text">
            <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4"><div className="text-dst-text-dim">集中度带宽</div><div className="mt-2 text-dst-text-title">{concentrationBandMeta[author.concentrationBand] ?? author.concentrationBand}</div></div>
            <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4"><div className="text-dst-text-dim">累计订阅占比</div><div className="mt-2 font-mono text-dst-text-title">{formatPercentValue(author.cumulativeSharePct)}</div></div>
            <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4"><div className="text-dst-text-dim">生产力分层</div><div className="mt-2 text-dst-text-title">{productivityBucketMeta[author.productivityBucket]}</div></div>
          </div>
        </Panel>

        <Panel title="作者常用标签" subtitle="按该作者全部作品里出现次数排序。">
          <div className="flex flex-wrap gap-2">{tagStats.length ? tagStats.map((item) => <TagPill key={item.tag}>{item.tag} · {item.count}</TagPill>) : <TagPill>暂无标签统计</TagPill>}</div>
        </Panel>
      </div>

      <Panel title="作者作品列表" subtitle="按订阅量从高到低排序。">
        <div className="table-shell overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-dst-dark text-dst-gold" style={{ fontVariant: 'small-caps', letterSpacing: '0.05em' }}>
              <tr>
                <th className="px-4 py-4 font-title font-medium">Mod</th>
                <th className="px-4 py-4 font-title font-medium">订阅量</th>
                <th className="px-4 py-4 font-title font-medium">好评率</th>
                <th className="px-4 py-4 font-title font-medium">维护时长</th>
                <th className="px-4 py-4 font-title font-medium">标签</th>
              </tr>
            </thead>
            <tbody>
              {authorMods.map((mod) => (
                <tr key={mod.id} className="table-row-alt border-t border-dst-border/30 align-top text-dst-text">
                  <td className="px-4 py-4">
                    <Link className="font-hans font-semibold text-dst-text-title hover:text-dst-gold" to={`/mod/${mod.id}`}>{mod.title}</Link>
                    <div className="mt-1 font-title text-xs text-dst-text-muted">Mod #{mod.rank}</div>
                  </td>
                  <td className="px-4 py-4 font-mono text-dst-gold">{formatNumber(mod.subscriptions)}</td>
                  <td className="px-4 py-4 font-mono">{formatRate(mod.positiveRate)}</td>
                  <td className="px-4 py-4 font-mono">{formatDays(mod.maintenanceDays)}</td>
                  <td className="px-4 py-4"><div className="flex flex-wrap gap-2">{mod.tags.slice(0, 4).map((tag) => <TagPill key={tag}>{tag}</TagPill>)}</div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
