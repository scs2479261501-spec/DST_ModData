import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import Panel from '../components/Panel';
import StatCard from '../components/StatCard';
import TagPill from '../components/TagPill';
import { loadAuthors, loadMods } from '../lib/data';
import { getQuadrantMeta } from '../lib/constants';
import { formatCompact, formatDate, formatDays, formatNumber, formatRate } from '../lib/format';

export default function ModDetailPage() {
  const { modId } = useParams();
  const [state, setState] = useState({ loading: true, error: null, mods: null, authors: null });

  useEffect(() => {
    let active = true;
    Promise.all([loadMods(), loadAuthors()])
      .then(([mods, authors]) => {
        if (active) {
          setState({ loading: false, error: null, mods, authors });
        }
      })
      .catch((error) => {
        if (active) {
          setState({ loading: false, error, mods: null, authors: null });
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const mod = useMemo(() => state.mods?.items.find((item) => item.id === modId) ?? null, [state.mods, modId]);
  const author = useMemo(() => state.authors?.items.find((item) => item.id === mod?.creatorId) ?? null, [state.authors, mod]);
  const modMap = useMemo(() => new Map((state.mods?.items ?? []).map((item) => [item.id, item])), [state.mods]);

  const sameAuthorMods = useMemo(() => {
    if (!author) return [];
    return author.mods.filter((id) => id !== mod?.id).map((id) => modMap.get(id)).filter(Boolean).sort((a, b) => b.subscriptions - a.subscriptions).slice(0, 8);
  }, [author, mod, modMap]);

  const relatedMods = useMemo(() => {
    if (!mod || !state.mods) return [];
    const tagSet = new Set(mod.tags);
    return state.mods.items.filter((item) => item.id !== mod.id && item.tags.some((tag) => tagSet.has(tag))).sort((a, b) => b.subscriptions - a.subscriptions).slice(0, 8);
  }, [state.mods, mod]);

  if (state.loading) return <LoadingState label="正在加载 Mod 详情…" />;
  if (state.error) return <EmptyState title="Mod 详情加载失败" description={state.error.message} />;
  if (!mod) {
    return <EmptyState title="没有找到对应的 Mod" description="这个 ID 不在当前站点的数据批次里，或者链接写错了。" action={<Link className="rounded-dst border border-dst-border bg-dst-brown px-4 py-2 font-hans text-sm text-dst-text hover:border-dst-gold hover:text-dst-gold" to="/mods">返回 Mod 排行</Link>} />;
  }

  const quadrant = getQuadrantMeta(mod.quadrant);
  const totalVotes = mod.votesUp + mod.votesDown;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow={`Mod #${mod.rank}`}
        title={mod.title}
        description="详情页聚合了这个 Mod 的核心指标、作者信息、标签信息，以及同作者和相似标签的其他作品，便于从排行榜快速下钻。"
        actions={
          <div className="flex gap-3">
            <a className="rounded-dst border border-dst-gold px-4 py-2 font-hans text-sm text-dst-gold transition-colors duration-300 hover:bg-dst-gold hover:text-dst-darkest" href={`https://steamcommunity.com/sharedfiles/filedetails/?id=${mod.id}`} target="_blank" rel="noopener noreferrer">Steam 页面 &#8599;</a>
            <Link className="rounded-dst border border-dst-border bg-dst-brown px-4 py-2 font-hans text-sm text-dst-text hover:border-dst-gold hover:text-dst-gold" to="/mods">返回排行榜</Link>
          </div>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="订阅量" value={formatNumber(mod.subscriptions)} hint={`全站排名 #${mod.rank}`} />
        <StatCard label="好评率" value={formatRate(mod.positiveRate)} hint={`好评 ${formatNumber(mod.votesUp)} / 差评 ${formatNumber(mod.votesDown)}`} />
        <StatCard label="维护时长" value={formatDays(mod.maintenanceDays)} hint={`中位线 ${formatDays(mod.maintenanceMedian)}`} />
        <StatCard label="距今最后更新" value={formatDays(mod.daysSinceLastUpdate)} hint={`总投票 ${formatNumber(totalVotes)}`} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel title="基本信息" subtitle="这里保留了活跃度分析需要的关键口径。">
          <dl className="grid gap-4 md:grid-cols-2">
            <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4"><dt className="font-hans text-sm text-dst-text-dim">Mod ID</dt><dd className="mt-2 font-mono text-dst-text">{mod.id}</dd></div>
            <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4"><dt className="font-hans text-sm text-dst-text-dim">作者 Steam ID</dt><dd className="mt-2 font-mono text-dst-text">{mod.creatorId}</dd></div>
            <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4"><dt className="font-hans text-sm text-dst-text-dim">创建时间</dt><dd className="mt-2 font-mono text-dst-text">{formatDate(mod.createdAt)}</dd></div>
            <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4"><dt className="font-hans text-sm text-dst-text-dim">最后更新时间</dt><dd className="mt-2 font-mono text-dst-text">{formatDate(mod.updatedAt)}</dd></div>
            <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4"><dt className="font-hans text-sm text-dst-text-dim">四象限</dt><dd className="mt-2"><span className={`inline-flex rounded-sm border px-3 py-1 text-xs ${quadrant.badgeClass}`}>{quadrant.label}</span></dd></div>
            <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4"><dt className="font-hans text-sm text-dst-text-dim">活跃度参考线</dt><dd className="mt-2 font-mono text-dst-text">订阅中位数 {formatNumber(mod.subscriptionMedian)} / 维护中位数 {formatDays(mod.maintenanceMedian)}</dd></div>
          </dl>
        </Panel>

        <Panel title="作者信息" subtitle="作者页会进一步展开其全部作品和集中度分层。">
          <div className="space-y-4">
            <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4"><div className="font-hans text-sm text-dst-text-dim">作者 ID</div><div className="mt-2 font-mono text-sm text-dst-text">{mod.creatorId}</div></div>
            {author ? (
              <>
                <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4"><div className="font-hans text-sm text-dst-text-dim">作者总订阅</div><div className="mt-2 font-mono text-xl font-semibold text-dst-gold">{formatCompact(author.totalSubscriptions)}</div></div>
                <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4"><div className="font-hans text-sm text-dst-text-dim">作者作品数</div><div className="mt-2 font-mono text-xl font-semibold text-dst-gold">{formatNumber(author.modCount)}</div></div>
                <Link className="inline-flex rounded-dst border border-dst-gold px-4 py-2 font-hans text-sm text-dst-gold transition-colors duration-300 hover:bg-dst-gold hover:text-dst-darkest" to={`/author/${author.id}`}>查看作者详情</Link>
              </>
            ) : (
              <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4 font-hans text-sm text-dst-text-dim">当前批次里没有找到该作者的聚合记录。</div>
            )}
          </div>
        </Panel>
      </div>

      <Panel title="标签" subtitle="来自预处理后的标签维表。"><div className="flex flex-wrap gap-2">{mod.tags.length ? mod.tags.map((tag) => <TagPill key={tag}>{tag}</TagPill>) : <TagPill>无标签</TagPill>}</div></Panel>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="同作者其他作品" subtitle="按订阅量排序。">
          <div className="space-y-3">
            {sameAuthorMods.length ? sameAuthorMods.map((item) => (
              <Link key={item.id} className="flex items-center justify-between rounded-dst border border-dst-border bg-dst-dark/50 px-4 py-4 transition-colors duration-300 hover:border-dst-gold" to={`/mod/${item.id}`}>
                <div><div className="font-hans font-semibold text-dst-text-title">{item.title}</div><div className="mt-1 font-hans text-sm text-dst-text-dim">#{item.rank} · 好评率 {formatRate(item.positiveRate)}</div></div>
                <div className="text-right font-mono text-sm text-dst-gold">{formatCompact(item.subscriptions)}</div>
              </Link>
            )) : <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4 font-hans text-sm text-dst-text-dim">该作者没有更多作品。</div>}
          </div>
        </Panel>

        <Panel title="相似标签作品" subtitle="按标签重合筛出高订阅 Mod。">
          <div className="space-y-3">
            {relatedMods.map((item) => (
              <Link key={item.id} className="flex items-center justify-between rounded-dst border border-dst-border bg-dst-dark/50 px-4 py-4 transition-colors duration-300 hover:border-dst-gold" to={`/mod/${item.id}`}>
                <div>
                  <div className="font-hans font-semibold text-dst-text-title">{item.title}</div>
                  <div className="mt-1 flex flex-wrap gap-2">{item.tags.slice(0, 3).map((tag) => <TagPill key={tag}>{tag}</TagPill>)}</div>
                </div>
                <div className="text-right font-mono text-sm text-dst-gold">{formatCompact(item.subscriptions)}</div>
              </Link>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
