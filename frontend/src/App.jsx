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

function ProfileStatusBanner() {
  const { user, logout } = useAuth();
  if (!user) {
    return (
      <div className="bg-slate-900 text-slate-300 px-4 py-1 text-xs border-b border-slate-800">
        <div className="mx-auto max-w-6xl flex flex-wrap items-center justify-between gap-2">
          <span className="text-slate-400">
            👋 Not logged in. <Link to="/login" className="text-amber-400 underline font-semibold ml-1">Log in here</Link> as <b>Admin</b> or <b>Citizen</b> to manage & verify complaints.
          </span>
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <span>Admin: <code>admin@civic.local</code></span>
            <span>•</span>
            <span>Citizen: <code>user@gmail.com</code></span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`px-4 py-1.5 text-xs border-b ${
      user.role === 'admin'
        ? 'bg-amber-950/80 border-amber-800 text-amber-200'
        : user.role === 'representative'
        ? 'bg-blue-950/80 border-blue-800 text-blue-200'
        : 'bg-emerald-950/80 border-emerald-800 text-emerald-200'
    }`}>
      <div className="mx-auto max-w-6xl flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span className="font-semibold text-white">Active Profile:</span>
          <span className="px-2 py-0.5 rounded font-black text-xs uppercase tracking-wide bg-white/20 text-white">
            {user.role === 'admin' ? '🛡️ Municipal Admin' : user.role === 'representative' ? '🏛️ Elected Representative' : '👤 Citizen'}
          </span>
          <span className="font-mono text-white/95 font-medium">({user.email})</span>
          {user.ward && <span className="text-white/70">• Ward: <b>{user.ward}</b></span>}
        </div>
        <div className="flex items-center gap-3">
          {user.role === 'admin' && (
            <Link to="/admin" className="font-bold underline text-amber-300 hover:text-white">
              Open Admin Portal →
            </Link>
          )}
          {user.role === 'representative' && (
            <Link to="/representative" className="font-bold underline text-blue-300 hover:text-white">
              Open Rep Portal →
            </Link>
          )}
          <button
            onClick={logout}
            className="text-xs font-bold text-red-300 hover:text-white underline cursor-pointer"
          >
            Log out / Switch Account
          </button>
        </div>
      </div>
    </div>
  );
}

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
          <div className="flex items-center gap-2 pl-2 border-l border-white/20">
            <div
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold ring-1 shadow-sm ${
                user.role === 'admin'
                  ? 'bg-amber-500/25 text-amber-200 ring-amber-400/50'
                  : user.role === 'representative'
                  ? 'bg-blue-500/25 text-blue-200 ring-blue-400/50'
                  : 'bg-emerald-500/25 text-emerald-200 ring-emerald-400/50'
              }`}
              title={`Logged in as: ${user.name || ''} (${user.email})`}
            >
              <span className="grid h-5 w-5 place-items-center rounded-full bg-signal text-[11px] font-black text-ink shadow-sm shrink-0">
                {user.role === 'admin' ? 'A' : user.role === 'representative' ? 'R' : 'U'}
              </span>
              <div className="text-left leading-tight">
                <span className="block font-black text-white text-[11px] max-w-[120px] truncate">
                  {user.role === 'admin' ? '🛡️ Admin' : user.role === 'representative' ? '🏛️ Rep' : '👤 User'}
                </span>
                <span className="block text-[9px] text-slate-300 font-mono truncate max-w-[120px]">
                  {user.email}
                </span>
              </div>
            </div>
            <button
              onClick={logout}
              className="rounded-md bg-white/10 px-2.5 py-1.5 text-xs font-bold text-slate-200 hover:bg-red-600 hover:text-white transition"
              title="Sign out of this account"
            >
              {t('logout')}
            </button>
          </div>
        ) : (
          <NavLink to="/login" className="btn btn-primary !py-1 text-xs font-bold">{t('login')}</NavLink>
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
      <ProfileStatusBanner />
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
