import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { api, media } from '../api';
import { useAuth } from '../auth';
import { StatusChip } from '../components';
import { CATS, STATUS, timeAgo, slaLabel } from '../lib';

const NEXT = {
  reported: ['under_review', 'assigned', 'in_progress'],
  under_review: ['assigned', 'in_progress', 'reported'],
  assigned: ['in_progress', 'resolved_awaiting_verification', 'verified_resolved', 'under_review'],
  in_progress: ['resolved_awaiting_verification', 'verified_resolved', 'assigned', 'under_review'],
  resolved_awaiting_verification: ['verified_resolved', 'in_progress'],
  verified_resolved: ['in_progress', 'under_review'],
};

const ACTION = {
  reported: 'Return to Reported',
  under_review: 'Start review',
  assigned: 'Assign to department',
  in_progress: 'Mark in progress',
  resolved_awaiting_verification: 'Mark resolved (request verification)',
  verified_resolved: 'Mark verified & closed',
};

const hours = (h) => (h == null ? 'No data' : h < 48 ? `${h} h` : `${(h / 24).toFixed(1)} days`);

const Stat = ({ label, value, sub, tone = '' }) => (
  <div className={`rounded-2xl bg-white p-4 ring-1 ring-slate-200 shadow-sm ${tone}`}>
    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</p>
    <p className="mt-1 text-2xl font-black text-slate-900">{value}</p>
    {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
  </div>
);

function ActionPanel({ c, deps, suggested, onDone }) {
  const options = NEXT[c.status] || [];
  const [next, setNext] = useState(options[0] || '');
  const [dept, setDept] = useState(c.department ? deps.find((d) => d.name === c.department)?.id || '' : '');
  const [note, setNote] = useState('');
  const [file, setFile] = useState(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const opts = NEXT[c.status] || [];
    setNext(opts[0] || '');
    setNote('');
    setFile(null);
    setErr('');
    const defaultDept = c.department
      ? deps.find((d) => d.name === c.department)?.id
      : (suggested || (deps.length > 0 ? deps[0].id : ''));
    setDept(defaultDept || '');
  }, [c.id, c.status, suggested, deps]);

  const submit = async (e) => {
    e.preventDefault();
    setErr('');
    const fd = new FormData();
    fd.append('status', next);
    fd.append('note', note);
    if (next === 'assigned') fd.append('department_id', dept);
    if (file) fd.append('after_image', file);
    setBusy(true);
    try {
      onDone(await api(`/admin/complaints/${c.id}/status`, { method: 'PATCH', form: fd }));
    } catch (x) {
      setErr(x.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-3 rounded-xl bg-slate-50 p-4 border border-slate-200 text-xs sm:text-sm">
      <p className="font-bold text-slate-900">Update Status Workflow</p>
      {c.status === 'resolved_awaiting_verification' && (
        <p className="text-xs text-slate-600">
          Waiting for the citizen or supporters to confirm. Send back to in_progress if further work is required.
        </p>
      )}
      {c.status === 'verified_resolved' && (
        <p className="text-xs text-emerald-700 font-medium">✓ Verified resolved by residents. Reopen only if problem recurs.</p>
      )}

      {options.length > 0 && (
        <label className="block text-xs font-semibold text-slate-700">
          Next Workflow State
          <select className="field mt-1 font-medium" value={next} onChange={(e) => setNext(e.target.value)}>
            {options.map((s) => (
              <option key={s} value={s}>{ACTION[s] || STATUS[s]?.label || s}</option>
            ))}
          </select>
        </label>
      )}

      {next === 'assigned' && (
        <label className="block text-xs font-semibold text-slate-700">
          Municipal Department
          <select required className="field mt-1" value={dept} onChange={(e) => setDept(e.target.value)}>
            <option value="">Choose department...</option>
            {deps.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </label>
      )}

      {(next === 'resolved_awaiting_verification' || next === 'verified_resolved') && (
        <label className="block text-xs font-semibold text-slate-700">
          Upload Completion Proof <span className="font-normal text-slate-400">(optional after-repair photo)</span>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setFile(e.target.files[0])}
            className="mt-1 block w-full text-xs file:mr-3 file:rounded-lg file:border-0 file:bg-ink file:px-3 file:py-1.5 file:text-white"
          />
        </label>
      )}

      <label className="block text-xs font-semibold text-slate-700">
        Officer Note for Public Timeline <span className="font-normal text-slate-400">(optional)</span>
        <input
          className="field mt-1"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="e.g. Work crew deployed, asphalt layered"
        />
      </label>

      {err && <p role="alert" className="rounded-lg bg-red-50 p-2 text-xs text-red-800">{err}</p>}

      <button disabled={busy || !next} className="btn btn-primary w-full font-bold">
        {busy ? 'Updating…' : 'Apply Workflow Transition'}
      </button>
    </form>
  );
}

export default function Admin() {
  const { user, ready } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [tab, setTab] = useState('complaints'); // complaints | moderation | analytics
  const [stats, setStats] = useState(null);
  const [items, setItems] = useState(null);
  const [deps, setDeps] = useState([]);
  const [reps, setReps] = useState([]);
  const [modQueue, setModQueue] = useState([]);
  const [f, setF] = useState({ status: '', category: '', feed: 'all' });
  const [sel, setSel] = useState(null);
  const [detail, setDetail] = useState(null);
  const [ins, setIns] = useState(null);
  const [err, setErr] = useState('');
  const [actionNotice, setActionNotice] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const loadStats = () => api('/admin/analytics').then(setStats).catch((e) => setErr(e.message));
  const loadList = () => {
    const q = new URLSearchParams({ feed: f.feed, limit: 100 });
    if (f.status) q.set('status', f.status);
    if (f.category) q.set('category', f.category);
    return api(`/complaints?${q}`).then(setItems).catch((e) => setErr(e.message));
  };
  const loadReps = () => api('/admin/representatives/pending').then(setReps).catch(() => {});
  const loadModeration = () => api('/admin/moderation').then(setModQueue).catch(() => {});

  const handleManualRefresh = async () => {
    setRefreshing(true);
    try {
      await Promise.allSettled([loadStats(), loadList(), loadReps(), loadModeration()]);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (!isAdmin) return;
    loadStats();
    loadReps();
    loadModeration();
    api('/admin/departments').then(setDeps).catch(() => {});
  }, [isAdmin]);

  useEffect(() => {
    if (isAdmin) loadList();
  }, [isAdmin, f]);

  // Periodic background refresh every 10 seconds so newly submitted citizen issues show up live
  useEffect(() => {
    if (!isAdmin) return;
    const timer = setInterval(() => {
      loadList();
      loadStats();
    }, 10000);
    return () => clearInterval(timer);
  }, [isAdmin, f]);

  useEffect(() => {
    if (sel) {
      api(`/complaints/${sel}`).then(setDetail).catch(() => {});
      api(`/admin/complaints/${sel}/insights`).then(setIns).catch(() => {});
    } else {
      setDetail(null);
      setIns(null);
    }
  }, [sel]);

  if (!ready) return null;
  if (!isAdmin) return <Navigate to="/" replace />;

  const s = stats?.by_status || {};
  const open = (stats?.total || 0) - (s.verified_resolved || 0);
  const done = (u) => {
    setItems((prev) => (prev ? prev.map((item) => (item.id === u.id ? { ...item, ...u } : item)) : prev));
    setDetail((d) => ({ ...d, ...u }));
    loadList();
    loadStats();
  };

  const verifyRep = async (id) => {
    await api(`/admin/representatives/${id}/verify`, { method: 'POST' });
    loadReps();
  };

  const triggerAutoEscalation = async () => {
    try {
      const res = await api('/admin/auto-escalate', { method: 'POST' });
      setActionNotice(res.message);
      loadStats();
      loadList();
      setTimeout(() => setActionNotice(''), 4000);
    } catch (e) {
      alert(e.message);
    }
  };

  const handleModeration = async (reportId, action) => {
    try {
      await api(`/admin/moderation/${reportId}/action`, { method: 'POST', body: { action } });
      loadModeration();
      loadList();
    } catch (e) {
      alert(e.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Municipal Administration Portal</h1>
          <p className="text-slate-600 text-sm">Pune Municipal Corporation (PMC) Operations Dashboard</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={triggerAutoEscalation}
            className="btn !bg-red-600 text-white text-xs font-bold shadow hover:!bg-red-700"
            title="Scan and auto-escalate overdue SLA complaints"
          >
            ⚡ Scan SLA & Auto-Escalate
          </button>
        </div>
      </div>

      {actionNotice && (
        <div className="rounded-xl bg-blue-50 border border-blue-200 p-3 text-xs font-semibold text-blue-900">
          {actionNotice}
        </div>
      )}

      {err && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{err}</p>}

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Total Filed" value={stats?.total ?? '…'} sub="Across all wards" />
        <Stat label="Active Open" value={stats ? open : '…'} sub="Needs resolution" />
        <Stat label="Awaiting Review" value={s.reported ?? 0} tone={s.reported ? 'ring-2 !ring-signal' : ''} sub="New submissions" />
        <Stat label="Awaiting Check" value={s.resolved_awaiting_verification ?? 0} sub="Pending citizen sign-off" />
        <Stat label="SLA Compliance" value={stats ? `${stats.sla_compliance_rate}%` : '…'} sub="Fixed on time" />
        <Stat label="Resident Rating" value={stats ? `⭐ ${stats.citizen_satisfaction}` : '…'} sub="Out of 5 stars" />
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-300 pb-1">
        <button
          onClick={() => setTab('complaints')}
          className={`px-4 py-2 text-sm font-bold border-b-2 ${tab === 'complaints' ? 'border-ink text-ink' : 'border-transparent text-slate-600'}`}
        >
          Issue Management
        </button>
        <button
          onClick={() => setTab('moderation')}
          className={`px-4 py-2 text-sm font-bold border-b-2 flex items-center gap-1.5 ${tab === 'moderation' ? 'border-ink text-ink' : 'border-transparent text-slate-600'}`}
        >
          Abuse Moderation Queue
          {modQueue.length > 0 && <span className="rounded-full bg-red-600 px-1.5 py-0.5 text-xs text-white">{modQueue.length}</span>}
        </button>
        <button
          onClick={() => setTab('analytics')}
          className={`px-4 py-2 text-sm font-bold border-b-2 ${tab === 'analytics' ? 'border-ink text-ink' : 'border-transparent text-slate-600'}`}
        >
          Ward & Department Analytics
        </button>
      </div>

      {/* Pending Representatives Notice */}
      {reps.length > 0 && (
        <section className="rounded-2xl border-2 border-signal bg-yellow-50 p-4">
          <h2 className="font-bold text-sm text-slate-900">Elected Representatives Awaiting Verification ({reps.length})</h2>
          <ul className="mt-2 space-y-2">
            {reps.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-white p-3 text-xs ring-1 ring-slate-200">
                <div>
                  <b className="text-slate-800">{r.name}</b> (Ward: {r.ward || 'General'})
                  <span className="block text-slate-500">{r.email}</span>
                </div>
                <button onClick={() => verifyRep(r.id)} className="btn btn-primary text-xs">Verify Credentials</button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* TAB 1: ISSUE MANAGEMENT */}
      {tab === 'complaints' && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_440px]">
          <section className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap gap-2">
                <select className="field !w-auto text-xs" value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}>
                  <option value="">All Statuses</option>
                  {Object.entries(STATUS).map(([k, v]) => (
                    <option key={k} value={k}>{v.label}</option>
                  ))}
                </select>
                <select className="field !w-auto text-xs" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>
                  <option value="">All Categories</option>
                  {Object.entries(CATS).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
                <select className="field !w-auto text-xs" value={f.feed} onChange={(e) => setF({ ...f, feed: e.target.value })}>
                  <option value="all">Newest First</option>
                  <option value="trending">Most Supported First</option>
                </select>
              </div>
              <button
                type="button"
                onClick={handleManualRefresh}
                disabled={refreshing}
                className="btn btn-secondary text-xs flex items-center gap-1.5"
                title="Refresh complaints list"
              >
                <span className={refreshing ? 'inline-block animate-spin' : ''}>🔄</span>
                {refreshing ? 'Refreshing…' : 'Refresh Data'}
              </button>
            </div>

            <div className="overflow-hidden rounded-2xl bg-white ring-1 ring-slate-200 shadow-sm">
              {items === null && <p className="p-6 text-center text-slate-500 text-sm">Loading complaints…</p>}
              {items?.length === 0 && <p className="p-8 text-center text-slate-600 text-sm">No complaints matching current filters.</p>}
              <ul className="divide-y divide-slate-100">
                {items?.map((c) => {
                  const sla = slaLabel(c.sla_hours_remaining, c.is_overdue);
                  return (
                    <li key={c.id}>
                      <button
                        onClick={() => setSel(c.id)}
                        className={`flex w-full items-center gap-3 p-3.5 text-left transition hover:bg-slate-50 ${
                          sel === c.id ? 'bg-amber-50 ring-1 ring-amber-300' : ''
                        }`}
                      >
                        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-slate-100 text-sm font-bold text-ink">
                          {c.counts.supports}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="block truncate font-bold text-sm text-slate-900">#{c.id} {c.title}</span>
                            {c.is_escalated && <span className="rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-bold text-white">ESCALATED</span>}
                          </div>
                          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 mt-0.5">
                            <span>{CATS[c.category] || c.category}</span>
                            {c.ward && <span>• 📍 {c.ward}</span>}
                            <span>• {timeAgo(c.created_at)}</span>
                            {sla && <span className={`rounded px-1.5 py-0.2 font-semibold ${sla.cls}`}>{sla.label}</span>}
                          </div>
                        </div>
                        <StatusChip status={c.status} />
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          </section>

          <aside>
            {!detail && (
              <div className="rounded-2xl bg-white p-8 text-center text-slate-600 ring-1 ring-slate-200 shadow-sm">
                <p className="font-bold text-slate-800">Select an Issue</p>
                <p className="mt-1 text-xs text-slate-500">Click any complaint from the list to inspect AI insights, repair evidence, and manage status.</p>
              </div>
            )}
            {detail && (
              <div className="space-y-4 rounded-2xl bg-white p-5 ring-1 ring-slate-200 shadow-sm lg:sticky lg:top-20">
                <div>
                  <div className="flex items-center justify-between">
                    <StatusChip status={detail.status} />
                    <span className="text-xs font-mono text-slate-500">Ref: #{detail.id}</span>
                  </div>
                  <h2 className="mt-2 text-lg font-bold text-slate-900 leading-snug">{detail.title}</h2>
                  <p className="mt-1 text-xs text-slate-600 leading-relaxed">{detail.description}</p>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  {detail.image_url && (
                    <figure className="overflow-hidden rounded-lg ring-1 ring-slate-200">
                      <img src={media(detail.image_url)} alt="Reported issue" className="h-28 w-full object-cover" />
                      <figcaption className="bg-slate-50 p-1 text-[11px] font-semibold text-slate-600 text-center">Citizen Photo</figcaption>
                    </figure>
                  )}
                  {detail.after_image_url && (
                    <figure className="overflow-hidden rounded-lg ring-1 ring-slate-200">
                      <img src={media(detail.after_image_url)} alt="After repair" className="h-28 w-full object-cover" />
                      <figcaption className="bg-emerald-50 p-1 text-[11px] font-semibold text-emerald-800 text-center">Repair Proof</figcaption>
                    </figure>
                  )}
                </div>

                {/* AI Officer Insights */}
                <div className="space-y-2 rounded-xl bg-indigo-50 p-4 text-xs">
                  <div className="flex items-center justify-between">
                    <p className="font-bold text-indigo-950">🤖 AI Municipal Assistant</p>
                    <span className="text-[10px] text-indigo-700 font-mono">Source: {ins?.summary?.source || 'Civic Engine'}</span>
                  </div>
                  {!ins ? (
                    <p className="text-slate-600">Generating officer briefing…</p>
                  ) : (
                    <>
                      <p className="text-slate-800 leading-relaxed">{ins.summary.text}</p>
                      {ins.suggested_department && (
                        <p className="text-indigo-900 font-medium">
                          🎯 Suggested Department: <b>{ins.suggested_department}</b>
                        </p>
                      )}
                      {ins.category_mismatch && (
                        <div className="rounded bg-yellow-100 p-2 text-yellow-900 font-medium">
                          ⚠️ Possible miscategorization: Photo indicates {CATS[ins.ai_category]} ({Math.round(ins.ai_confidence * 100)}% sure).
                        </div>
                      )}
                      {ins.evidence_flag && (
                        <div role="alert" className="rounded bg-red-100 p-2 text-red-950 font-semibold">
                          🚨 Evidence Warning: {ins.evidence_flag}
                        </div>
                      )}
                    </>
                  )}
                </div>

                <ActionPanel c={detail} deps={deps} suggested={ins?.suggested_department_id} onDone={done} />

                <div className="pt-2 border-t border-slate-100 flex justify-between text-xs">
                  <Link to={`/issues/${detail.id}`} className="font-semibold text-blue-700 underline">
                    Open Citizen View & Discussion →
                  </Link>
                  <a
                    className="text-slate-500 underline"
                    target="_blank"
                    rel="noreferrer"
                    href={`https://www.openstreetmap.org/?mlat=${detail.latitude}&mlon=${detail.longitude}#map=18/${detail.latitude}/${detail.longitude}`}
                  >
                    Open in OSM
                  </a>
                </div>
              </div>
            )}
          </aside>
        </div>
      )}

      {/* TAB 2: MODERATION QUEUE */}
      {tab === 'moderation' && (
        <section className="space-y-4 rounded-2xl bg-white p-6 ring-1 ring-slate-200 shadow-sm">
          <h2 className="text-xl font-bold">Community Abuse & Spam Reports</h2>
          <p className="text-xs text-slate-600">Review flagged complaints and comments submitted by citizens to maintain civil, constructive engagement.</p>

          {modQueue.length === 0 && (
            <div className="py-8 text-center text-slate-500 text-sm">
              ✓ No pending reports. All community submissions are clean.
            </div>
          )}

          <ul className="space-y-3">
            {modQueue.map((r) => (
              <li key={r.id} className="rounded-xl border border-slate-200 p-4 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-800 capitalize">
                    Flagged {r.target_type} • Reason: <span className="text-red-600">{r.reason.replace(/_/g, ' ')}</span>
                  </span>
                  <span className="text-slate-500">Reported by {r.reporter.name} ({timeAgo(r.created_at)})</span>
                </div>
                {r.details && <p className="text-slate-600 italic bg-slate-50 p-2 rounded">"{r.details}"</p>}
                <div className="rounded bg-slate-50 p-2 text-slate-800 font-medium">
                  {r.target_type === 'complaint' ? (
                    <div><b>Title:</b> {r.target_info?.title}<br /><b>Description:</b> {r.target_info?.description}</div>
                  ) : (
                    <div><b>Comment:</b> {r.target_info?.body} (on Issue #{r.target_info?.complaint_id})</div>
                  )}
                </div>
                <div className="flex gap-2 pt-1">
                  <button onClick={() => handleModeration(r.id, 'hide')} className="btn !bg-red-600 text-white text-xs !py-1">
                    Hide Content
                  </button>
                  {r.target_type === 'comment' && (
                    <button onClick={() => handleModeration(r.id, 'delete_comment')} className="btn !bg-red-700 text-white text-xs !py-1">
                      Delete Comment
                    </button>
                  )}
                  <button onClick={() => handleModeration(r.id, 'dismiss')} className="btn btn-ghost text-xs !py-1">
                    Dismiss (Legitimate Content)
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* TAB 3: WARD & DEPARTMENT ANALYTICS */}
      {tab === 'analytics' && stats && (
        <section className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-2xl bg-white p-5 ring-1 ring-slate-200 shadow-sm">
              <h3 className="font-bold text-base text-slate-900 mb-3">Complaints by Category</h3>
              <ul className="space-y-2 text-xs">
                {Object.entries(stats.by_category).sort((a, b) => b[1] - a[1]).map(([k, n]) => (
                  <li key={k} className="flex items-center gap-3">
                    <span className="w-32 shrink-0 font-medium">{CATS[k] || k}</span>
                    <div className="h-3 flex-1 rounded bg-slate-100 overflow-hidden">
                      <div className="h-full bg-ink rounded" style={{ width: `${(n / (stats.total || 1)) * 100}%` }} />
                    </div>
                    <span className="w-8 text-right font-bold text-slate-700">{n}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-2xl bg-white p-5 ring-1 ring-slate-200 shadow-sm">
              <h3 className="font-bold text-base text-slate-900 mb-3">Ward Activity Leaderboard</h3>
              <ul className="space-y-2 text-xs">
                {Object.entries(stats.by_ward || {}).sort((a, b) => b[1] - a[1]).map(([w, n]) => (
                  <li key={w} className="flex items-center gap-3">
                    <span className="w-32 shrink-0 font-medium">📍 {w}</span>
                    <div className="h-3 flex-1 rounded bg-slate-100 overflow-hidden">
                      <div className="h-full bg-signal rounded" style={{ width: `${(n / (stats.total || 1)) * 100}%` }} />
                    </div>
                    <span className="w-8 text-right font-bold text-slate-700">{n}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
