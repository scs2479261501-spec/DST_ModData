import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import Panel from '../components/Panel';
import StatCard from '../components/StatCard';
import TagPill from '../components/TagPill';
import { loadAuthors, loadDimTags, loadMods, loadOverview } from '../lib/data';
import { metricLabels } from '../lib/constants';
import { formatCompact, formatNumber, formatRate } from '../lib/format';

export default function HomePage() {
  const [state, setState] = useState({ loading: true, error: null, overview: null, dimTags: null, mods: null, authors: null });

  useEffect(() => {
    let active = true;
    Promise.all([loadOverview(), loadDimTags(), loadMods(), loadAuthors()])
      .then(([overview, dimTags, mods, authors]) => {
        if (active) {
          setState({ loading: false, error: null, overview, dimTags, mods, authors });
        }
      })
      .catch((error) => {
        if (active) {
          setState({ loading: false, error, overview: null, dimTags: null, mods: null, authors: null });
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (state.loading) {
    return <LoadingState label="正在加载首页概览…" />;
  }
  if (state.error) {
    return <EmptyState title="首页数据加载失败" description={state.error.message} />;
  }

  const topTags = state.dimTags.items.slice(0, 18);
  const topMods = state.mods.items.slice(0, 8);
  const topAuthors = state.authors.items.slice(0, 6);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Overview"
        title="数据来自 DST 创意工坊"
        description={`当前站点覆盖 ${state.overview.items.find((m) => m.key === 'mod_count')?.display ?? formatNumber(state.mods.meta.rowCount)} 个 Mod、${state.overview.items.find((m) => m.key === 'author_count')?.display ?? formatNumber(state.authors.meta.rowCount)} 位作者，以及完整的标签、活跃度、作者和评论分析输出。其余页面围绕这些事实表做深入浏览。`}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {state.overview.items.map((metric) => (
          <StatCard
            key={metric.key}
            label={metricLabels[metric.key] ?? metric.label}
            value={metric.display}
            hint={metric.key === 'subscription_median' || metric.key === 'maintenance_median' ? '四象限分桶参考线' : `来自 ${state.overview.meta.batchDate ?? ''} 全量批次`}
          />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel title="浏览入口">
          <div className="grid gap-4 md:grid-cols-2">
            {[
              ['Mod 排行', '/mods', '查看Mod排行和Mod详情页。'],
              ['作者分析', '/authors', '看头部集中度、作者分层和代表性作品。'],
              ['标签供需', '/supply-demand', '直接找蓝海、红海和拥挤但强势的标签。'],
              ['活跃度', '/activity', '用订阅量和维护时长查看四象限结构。'],
              ['评论分析', '/comments', '比较高订阅与中位订阅 Mod 的评论关键词差异。'],
            ].map(([label, href, description]) => (
              <Link key={href} className="panel-soft block p-5 transition-all duration-300 hover:-translate-y-px hover:border-dst-gold" to={href}>
                <div className="font-title text-base font-semibold text-dst-text-title">{label}</div>
                <p className="mt-2 font-hans text-sm leading-6 text-dst-text-dim">{description}</p>
              </Link>
            ))}
          </div>
        </Panel>

        <Panel title="数据范围">
          <div className="space-y-4 font-hans text-sm leading-7 text-dst-text">
            <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4">
              <div className="text-dst-text-dim">Mod 主表</div>
              <div className="mt-1 font-mono text-xl font-semibold text-dst-gold">{state.overview.items.find((m) => m.key === 'mod_count')?.display ?? formatNumber(state.mods.meta.rowCount)} 条</div>
              <div className="mt-2 text-dst-text-dim">用于 Mod 排行、详情页和活跃度页。</div>
            </div>
            <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4">
              <div className="text-dst-text-dim">作者聚合表</div>
              <div className="mt-1 font-mono text-xl font-semibold text-dst-gold">{state.overview.items.find((m) => m.key === 'author_count')?.display ?? formatNumber(state.authors.meta.rowCount)} 位</div>
              <div className="mt-2 text-dst-text-dim">用于作者排行、作者详情和头部集中度曲线。</div>
            </div>
            <div className="rounded-dst border border-dst-border bg-dst-dark/50 p-4">
              <div className="text-dst-text-dim">标签维表</div>
              <div className="mt-1 font-mono text-xl font-semibold text-dst-gold">{formatNumber(state.dimTags.meta.rowCount)} 个</div>
              <div className="mt-2 text-dst-text-dim">用于首页词云、全站标签筛选和供需矩阵散点图。</div>
            </div>
          </div>
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="头部 Mod 预览" subtitle="按订阅量排名的前 8 个作品。">
          <div className="grid gap-4 md:grid-cols-2">
            {topMods.map((mod) => (
              <Link key={mod.id} className="panel-soft p-4 transition-all duration-300 hover:-translate-y-px hover:border-dst-gold" to={`/mod/${mod.id}`}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="font-title text-xs uppercase tracking-[0.2em] text-dst-text-muted">#{mod.rank}</div>
                    <div className="mt-2 line-clamp-2 font-hans text-base font-semibold text-dst-text-title">{mod.title}</div>
                  </div>
                  <div className="rounded-sm border border-dst-gold/30 bg-dst-gold/10 px-3 py-1 font-mono text-xs text-dst-gold">{formatCompact(mod.subscriptions)}</div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {mod.tags.slice(0, 4).map((tag) => (
                    <TagPill key={tag}>{tag}</TagPill>
                  ))}
                </div>
                <div className="mt-4 font-hans text-sm text-dst-text-dim">好评率 {formatRate(mod.positiveRate)}</div>
              </Link>
            ))}
          </div>
        </Panel>

        <Panel title="头部作者预览" subtitle="按总订阅量排名的前 6 位作者。">
          <div className="space-y-3">
            {topAuthors.map((author) => (
              <Link key={author.id} className="flex items-center justify-between gap-4 rounded-dst border border-dst-border bg-dst-dark/50 px-4 py-4 transition-all duration-300 hover:-translate-y-px hover:border-dst-gold" to={`/author/${author.id}`}>
                <div>
                  <div className="font-title text-xs uppercase tracking-[0.22em] text-dst-text-muted">作者 #{author.rank}</div>
                  <div className="mt-2 font-mono text-sm text-dst-text">{author.id}</div>
                  <div className="mt-2 font-hans text-sm text-dst-text-dim">{formatNumber(author.modCount)} 个 Mod · 平均订阅 {formatCompact(author.avgSubscriptions)}</div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-xl font-semibold text-dst-gold">{formatCompact(author.totalSubscriptions)}</div>
                  <div className="mt-1 font-hans text-sm text-dst-text-dim">全站前列作者</div>
                </div>
              </Link>
            ))}
          </div>
        </Panel>
      </div>

      <Panel title="标签词云" subtitle="字体大小按标签覆盖的 Mod 数量缩放。">
        <div className="flex flex-wrap gap-3">
          {topTags.map((tag) => {
            const size = 0.95 + Math.log10(tag.weight + 1) * 0.55;
            return (
              <TagPill key={tag.tag} style={{ fontSize: `${size}rem` }}>
                {tag.tag} · {formatNumber(tag.modCount)}
              </TagPill>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}
