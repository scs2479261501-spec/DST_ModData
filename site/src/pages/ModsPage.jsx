import { useDeferredValue, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import EmptyState from '../components/EmptyState';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import Panel from '../components/Panel';
import TagPill from '../components/TagPill';
import { loadDimTags, loadMods } from '../lib/data';
import { getQuadrantMeta, quadrantMeta } from '../lib/constants';
import { formatDays, formatNumber, formatRate } from '../lib/format';

const pageSize = 50;

export default function ModsPage() {
  const [state, setState] = useState({ loading: true, error: null, mods: null, dimTags: null });
  const [query, setQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState('全部');
  const [selectedQuadrant, setSelectedQuadrant] = useState('全部');
  const [sortBy, setSortBy] = useState('rank');
  const [page, setPage] = useState(1);
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());

  useEffect(() => {
    let active = true;
    Promise.all([loadMods(), loadDimTags()])
      .then(([mods, dimTags]) => {
        if (active) {
          setState({ loading: false, error: null, mods, dimTags });
        }
      })
      .catch((error) => {
        if (active) {
          setState({ loading: false, error, mods: null, dimTags: null });
        }
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    setPage(1);
  }, [deferredQuery, selectedTag, selectedQuadrant, sortBy]);

  const filteredMods = useMemo(() => {
    if (!state.mods) return [];
    let next = state.mods.items;
    if (deferredQuery) {
      next = next.filter((mod) => mod.searchKey.includes(deferredQuery) || mod.id.includes(deferredQuery));
    }
    if (selectedTag !== '全部') {
      next = next.filter((mod) => mod.tags.includes(selectedTag));
    }
    if (selectedQuadrant !== '全部') {
      next = next.filter((mod) => mod.quadrant === selectedQuadrant);
    }
    const sorted = [...next];
    switch (sortBy) {
      case 'positiveRate':
        sorted.sort((a, b) => b.positiveRate - a.positiveRate || b.subscriptions - a.subscriptions);
        break;
      case 'recentUpdate':
        sorted.sort((a, b) => a.daysSinceLastUpdate - b.daysSinceLastUpdate || b.subscriptions - a.subscriptions);
        break;
      case 'maintenance':
        sorted.sort((a, b) => b.maintenanceDays - a.maintenanceDays || b.subscriptions - a.subscriptions);
        break;
      case 'votes':
        sorted.sort((a, b) => b.votesUp - a.votesUp || b.subscriptions - a.subscriptions);
        break;
      default:
        sorted.sort((a, b) => a.rank - b.rank);
    }
    return sorted;
  }, [state.mods, deferredQuery, selectedTag, selectedQuadrant, sortBy]);

  if (state.loading) return <LoadingState label="正在加载 Mod 列表…" />;
  if (state.error) return <EmptyState title="Mod 列表加载失败" description={state.error.message} />;

  const totalPages = Math.max(1, Math.ceil(filteredMods.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pageItems = filteredMods.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const topTags = state.dimTags.items.slice(0, 20);

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Mods" title="Mod 排行榜与筛选浏览" description="默认按订阅量排序，支持按关键词、标签、四象限和不同指标排序。由于数据量接近全量，列表页只做分页展示，详情页再看单个 Mod。" />

      <Panel title="筛选与排序" subtitle="客户端本地过滤，不依赖浏览器存储。">
        <div className="grid gap-4 lg:grid-cols-[2fr_1fr_1fr_1fr]">
          <label>
            <div className="mb-2 font-hans text-sm text-dst-text-dim">搜索 Mod 名称或 ID</div>
            <input className="input-dark" onChange={(event) => setQuery(event.target.value)} placeholder="例如 Combined Status / 376333686" value={query} />
          </label>
          <label>
            <div className="mb-2 font-hans text-sm text-dst-text-dim">标签</div>
            <select className="input-dark" onChange={(event) => setSelectedTag(event.target.value)} value={selectedTag}>
              <option value="全部">全部标签</option>
              {topTags.map((tag) => (
                <option key={tag.tag} value={tag.tag}>{tag.tag}</option>
              ))}
            </select>
          </label>
          <label>
            <div className="mb-2 font-hans text-sm text-dst-text-dim">四象限</div>
            <select className="input-dark" onChange={(event) => setSelectedQuadrant(event.target.value)} value={selectedQuadrant}>
              <option value="全部">全部象限</option>
              {Object.entries(quadrantMeta).map(([key, meta]) => (
                <option key={key} value={key}>{meta.label}</option>
              ))}
            </select>
          </label>
          <label>
            <div className="mb-2 font-hans text-sm text-dst-text-dim">排序</div>
            <select className="input-dark" onChange={(event) => setSortBy(event.target.value)} value={sortBy}>
              <option value="rank">订阅量（默认）</option>
              <option value="positiveRate">好评率</option>
              <option value="recentUpdate">最近更新</option>
              <option value="maintenance">维护时长</option>
              <option value="votes">好评票数</option>
            </select>
          </label>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2 font-hans text-sm text-dst-text-dim">
          <span>命中 {formatNumber(filteredMods.length)} 条</span>
          {selectedTag !== '全部' ? <TagPill>{selectedTag}</TagPill> : null}
          {selectedQuadrant !== '全部' ? <TagPill>{getQuadrantMeta(selectedQuadrant).label}</TagPill> : null}
        </div>
      </Panel>

      <div className="table-shell overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-dst-dark text-dst-gold" style={{ fontVariant: 'small-caps', letterSpacing: '0.05em' }}>
            <tr>
              <th className="px-4 py-4 font-title font-medium">排名</th>
              <th className="px-4 py-4 font-title font-medium">Mod</th>
              <th className="px-4 py-4 font-title font-medium">订阅量</th>
              <th className="px-4 py-4 font-title font-medium">好评率</th>
              <th className="px-4 py-4 font-title font-medium">维护时长</th>
              <th className="px-4 py-4 font-title font-medium">距今未更新</th>
              <th className="px-4 py-4 font-title font-medium">象限</th>
              <th className="px-4 py-4 font-title font-medium">作者</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.map((mod) => {
              const quadrant = getQuadrantMeta(mod.quadrant);
              return (
                <tr key={mod.id} className="table-row-alt border-t border-dst-border/30 align-top text-dst-text">
                  <td className="px-4 py-4 font-mono text-dst-text-dim">#{mod.rank}</td>
                  <td className="px-4 py-4">
                    <Link className="font-hans font-semibold text-dst-text-title hover:text-dst-gold" to={`/mod/${mod.id}`}>{mod.title}</Link>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {mod.tags.slice(0, 4).map((tag) => <TagPill key={tag}>{tag}</TagPill>)}
                    </div>
                  </td>
                  <td className="px-4 py-4 font-mono text-dst-gold">{formatNumber(mod.subscriptions)}</td>
                  <td className="px-4 py-4 font-mono">{formatRate(mod.positiveRate)}</td>
                  <td className="px-4 py-4 font-mono">{formatDays(mod.maintenanceDays)}</td>
                  <td className="px-4 py-4 font-mono">{formatDays(mod.daysSinceLastUpdate)}</td>
                  <td className="px-4 py-4"><span className={`inline-flex rounded-sm border px-3 py-1 text-xs ${quadrant.badgeClass}`}>{quadrant.label}</span></td>
                  <td className="px-4 py-4"><Link className="font-mono text-dst-text-dim hover:text-dst-gold" to={`/author/${mod.creatorId}`}>{mod.creatorId}</Link></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="font-hans text-sm text-dst-text-dim">第 {formatNumber(currentPage)} / {formatNumber(totalPages)} 页，每页 {pageSize} 条</div>
        <div className="flex gap-3">
          <button className="rounded-dst border border-dst-border bg-dst-brown px-4 py-2 font-hans text-sm text-dst-text transition-colors duration-300 hover:border-dst-gold hover:text-dst-gold disabled:cursor-not-allowed disabled:opacity-40" disabled={currentPage <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))} type="button">上一页</button>
          <button className="rounded-dst border border-dst-border bg-dst-brown px-4 py-2 font-hans text-sm text-dst-text transition-colors duration-300 hover:border-dst-gold hover:text-dst-gold disabled:cursor-not-allowed disabled:opacity-40" disabled={currentPage >= totalPages} onClick={() => setPage((value) => Math.min(totalPages, value + 1))} type="button">下一页</button>
        </div>
      </div>
    </div>
  );
}
