import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { useTranslation } from '../i18n';
import { ComplaintCard, MapView } from '../components';
import { CATS, PUNE } from '../lib';

export default function Feed() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [tab, setTab] = useState('nearby');
  const [cat, setCat] = useState('');
  const [view, setView] = useState('list');
  const [pos, setPos] = useState(PUNE);
  const [located, setLocated] = useState(false);
  const [items, setItems] = useState(null);
  const [err, setErr] = useState('');

  const TABS = [
    ['nearby', t('tab_nearby')],
    ['trending', t('tab_trending')],
    ['all', t('tab_all')],
    ['following', t('tab_following')],
    ['mine', t('tab_mine')],
  ];

  useEffect(() => {
    navigator.geolocation?.getCurrentPosition(
      (p) => {
        setPos([p.coords.latitude, p.coords.longitude]);
        setLocated(true);
      },
      () => {}
    );
  }, []);

  useEffect(() => {
    if ((tab === 'mine' || tab === 'following') && !user) {
      setItems([]);
      return;
    }
    setItems(null);
    setErr('');
    const q = new URLSearchParams({ feed: tab });
    if (tab === 'nearby') {
      q.set('lat', pos[0]);
      q.set('lng', pos[1]);
      q.set('radius_km', 5);
    }
    if (cat) q.set('category', cat);
    api(`/complaints?${q}`)
      .then(setItems)
      .catch((e) => setErr(e.message));
  }, [tab, cat, pos, user]);

  const replace = (u) => setItems((list) => list.map((x) => (x.id === u.id ? u : x)));

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-xl">
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">{t('feed_title')}</h1>
          <p className="mt-1 text-slate-600 text-sm">
            {tab === 'nearby' && !located
              ? 'Showing issues across Pune. Allow GPS location to prioritize your immediate neighborhood.'
              : t('feed_subtitle')}
          </p>
        </div>
        <select
          aria-label="Category"
          className="field !w-auto bg-white shadow-sm font-medium"
          value={cat}
          onChange={(e) => setCat(e.target.value)}
        >
          <option value="">{t('all_categories')}</option>
          {Object.entries(CATS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>

      <div className="mb-5 flex gap-1 overflow-x-auto border-b border-slate-300">
        {TABS.map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`-mb-px whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-semibold transition ${
              tab === k ? 'border-ink text-ink font-bold' : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            {label}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-1 pb-1 lg:hidden">
          {['list', 'map'].map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`btn !py-1 text-xs ${view === v ? 'bg-ink text-white' : 'btn-ghost'}`}
            >
              {v === 'list' ? 'List' : 'Map'}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_400px]">
        <section className={`space-y-4 ${view === 'map' ? 'hidden lg:block' : ''}`}>
          {err && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{err}</p>}
          {items === null && !err && <p className="text-slate-500 py-8 text-center">Loading civic issues…</p>}
          {items?.length === 0 && (
            <div className="rounded-2xl bg-white p-8 text-center ring-1 ring-slate-200 shadow-sm">
              <p className="font-bold text-lg text-slate-800">
                {tab === 'mine' && !user
                  ? 'Log in to see your filed reports.'
                  : tab === 'following' && !user
                  ? 'Log in to view complaints and wards you follow.'
                  : tab === 'following'
                  ? 'You are not following any complaints or wards yet. Click "Follow" on any issue to track it here.'
                  : 'No complaints found here.'}
              </p>
              <p className="mt-2 text-sm text-slate-600">
                Spot a pothole, open garbage dump or broken streetlight? Report it directly to municipal officials.
              </p>
              <Link to="/report" className="btn btn-primary mt-4 font-semibold">
                {t('report_issue')}
              </Link>
            </div>
          )}
          {items?.map((c) => (
            <ComplaintCard key={c.id} c={c} onChange={replace} />
          ))}
        </section>

        <aside className={`${view === 'list' ? 'hidden lg:block' : ''}`}>
          <div className="lg:sticky lg:top-24">
            <div className="mb-2 flex items-center justify-between text-xs text-slate-500 px-1">
              <span>Interactive Ward Map</span>
              <span>{items?.length || 0} issues shown</span>
            </div>
            <MapView items={items || []} center={pos} className="h-[65vh] lg:h-[540px] shadow-sm" />
          </div>
        </aside>
      </div>
    </div>
  );
}
