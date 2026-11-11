import { useEffect, useState } from 'react';
import { Link, NavLink, Route, Routes, Navigate, useLocation } from 'react-router-dom';
import { api } from './api';
import { useAuth } from './auth';
import { useTranslation } from './i18n';
import Feed from './pages/Feed.jsx';
import Auth from './pages/Auth.jsx';
import Report from './pages/Report.jsx';
import Detail from './pages/Detail.jsx';
import Notifications from './pages/Notifications.jsx';
import Admin from './pages/Admin.jsx';
import Updates from './pages/Updates.jsx';
import Representative from './pages/Representative.jsx';

function Header() {
  const { user, logout } = useAuth();
  const { t, lang, setLanguage } = useTranslation();
  const [unread, setUnread] = useState(0);
  const loc = useLocation();

  useEffect(() => {
    if (user) {
      api('/notifications')
        .then((n) => setUnread(n.filter((x) => !x.is_read).length))
        .catch(() => {});
    } else {
      setUnread(0);
    }
  }, [user, loc.pathname]);

  const link = ({ isActive }) =>
    `rounded-md px-3 py-1.5 text-sm ${isActive ? 'bg-white/15 font-bold' : 'hover:bg-white/10'}`;

  return (
    <header className="sticky top-0 z-30 bg-ink text-white shadow-md">
      <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
        <Link to="/" className="mr-auto flex items-center gap-2 text-lg font-bold">
          <span className="grid h-7 w-7 place-items-center rounded bg-signal text-sm font-black text-ink shadow">C</span>
          <span className="hidden sm:inline">{t('app_title')}</span>
          <span className="inline sm:hidden">Civic Connect</span>
        </Link>

        {/* Language Switcher */}
        <div className="flex items-center rounded-lg bg-white/10 p-0.5 text-xs">
          <button
            onClick={() => setLanguage('en')}
            className={`rounded px-2 py-1 ${lang === 'en' ? 'bg-signal font-bold text-ink' : 'text-slate-300 hover:text-white'}`}
          >
            EN
          </button>
          <button
            onClick={() => setLanguage('mr')}
            className={`rounded px-2 py-1 ${lang === 'mr' ? 'bg-signal font-bold text-ink' : 'text-slate-300 hover:text-white'}`}
          >
            मराठी
          </button>
          <button
            onClick={() => setLanguage('hi')}
            className={`rounded px-2 py-1 ${lang === 'hi' ? 'bg-signal font-bold text-ink' : 'text-slate-300 hover:text-white'}`}
          >
            हिंदी
          </button>
        </div>

        <NavLink to="/" end className={link}>{t('issues_near_you')}</NavLink>
        <NavLink to="/updates" className={link}>{t('dev_updates')}</NavLink>
        {user?.role === 'representative' && <NavLink to="/representative" className={link}>{t('my_portal')}</NavLink>}
        {user?.role === 'admin' && <NavLink to="/admin" className={link}>{t('dashboard')}</NavLink>}
        {user && (
          <NavLink to="/notifications" className={link}>
            {t('notifications')}
            {unread > 0 && <span className="ml-1.5 rounded-full bg-signal px-1.5 text-xs text-ink font-bold">{unread}</span>}
          </NavLink>
        )}
        <Link to="/report" className="btn btn-primary !py-1.5 shadow-sm font-semibold">{t('report_issue')}</Link>
        {user ? (
          <button onClick={logout} className="rounded-md px-3 py-1.5 text-sm text-slate-300 hover:bg-white/10 hover:text-white">
            {t('logout')}
          </button>
        ) : (
          <NavLink to="/login" className={link}>{t('login')}</NavLink>
        )}
      </div>
    </header>
  );
}

function Private({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return null;
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Feed />} />
          <Route path="/login" element={<Auth mode="login" />} />
          <Route path="/register" element={<Auth mode="register" />} />
          <Route path="/report" element={<Private><Report /></Private>} />
          <Route path="/issues/:id" element={<Detail />} />
          <Route path="/updates" element={<Updates />} />
          <Route path="/representative" element={<Private><Representative /></Private>} />
          <Route path="/admin" element={<Private><Admin /></Private>} />
          <Route path="/notifications" element={<Private><Notifications /></Private>} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}
