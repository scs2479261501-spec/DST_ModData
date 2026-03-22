import { lazy, Suspense } from 'react';
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom';
import LoadingState from './components/LoadingState';
import SiteShell from './components/SiteShell';

const ActivityPage = lazy(() => import('./pages/ActivityPage'));
const AuthorDetailPage = lazy(() => import('./pages/AuthorDetailPage'));
const AuthorsPage = lazy(() => import('./pages/AuthorsPage'));
const CommentsPage = lazy(() => import('./pages/CommentsPage'));
const HomePage = lazy(() => import('./pages/HomePage'));
const ModDetailPage = lazy(() => import('./pages/ModDetailPage'));
const ModsPage = lazy(() => import('./pages/ModsPage'));
const SupplyDemandPage = lazy(() => import('./pages/SupplyDemandPage'));

export default function App() {
  return (
    <HashRouter>
      <SiteShell>
        <Suspense fallback={<LoadingState label="正在加载页面模块…" />}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/mods" element={<ModsPage />} />
            <Route path="/mod/:modId" element={<ModDetailPage />} />
            <Route path="/authors" element={<AuthorsPage />} />
            <Route path="/author/:authorId" element={<AuthorDetailPage />} />
            <Route path="/supply-demand" element={<SupplyDemandPage />} />
            <Route path="/activity" element={<ActivityPage />} />
            <Route path="/comments" element={<CommentsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </SiteShell>
    </HashRouter>
  );
}