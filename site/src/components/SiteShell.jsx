import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { loadOverview } from '../lib/data';

const navItems = [
  { to: '/', label: '概览' },
  { to: '/mods', label: 'Mod 排行' },
  { to: '/authors', label: '作者分析' },
  { to: '/supply-demand', label: '标签供需' },
  { to: '/activity', label: '活跃度' },
  { to: '/comments', label: '评论分析' },
];

function linkClass({ isActive }) {
  return [
    'px-4 py-2 text-sm font-body transition-colors duration-200 border-b-2',
    isActive
      ? 'border-dst-gold text-dst-gold'
      : 'border-transparent text-dst-text-dim hover:text-dst-gold',
  ].join(' ');
}

export default function SiteShell({ children }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [batchDate, setBatchDate] = useState('');

  useEffect(() => {
    loadOverview().then((o) => setBatchDate(o.meta.batchDate ?? '')).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-dst-border bg-dst-dark shadow-navbar">
        <div className="mx-auto flex max-w-[1200px] flex-col gap-3 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h1 className="font-title text-xl font-semibold tracking-[2px] text-dst-gold sm:text-2xl">
                DST Mod Explorer
              </h1>
              <p className="mt-1 max-w-3xl font-hans text-sm text-dst-text-dim">
                基于 Steam 创意工坊《饥荒联机版》Mod 全量抓取和分析结果构建的静态数据站点
              </p>
            </div>
            {/* Mobile hamburger */}
            <button
              className="text-dst-gold sm:hidden"
              onClick={() => setMenuOpen((v) => !v)}
              type="button"
              aria-label="Toggle menu"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="h-6 w-6">
                {menuOpen
                  ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  : <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                }
              </svg>
            </button>
          </div>
          <nav className={`overflow-x-auto pb-1 ${menuOpen ? 'block' : 'hidden sm:block'}`}>
            <div className="flex min-w-max gap-1 sm:gap-2">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  className={linkClass}
                  end={item.to === '/'}
                  to={item.to}
                  onClick={() => setMenuOpen(false)}
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-[1200px] px-4 py-8 sm:px-6 lg:px-8">{children}</main>

      <footer className="border-t border-dashed border-dst-border py-6 text-center font-hans text-sm text-dst-text-muted">
        数据采集于 {batchDate || '...'} · 基于 Steam Web API 与公开页面 · DST Mod 生态分析项目
      </footer>
    </div>
  );
}
