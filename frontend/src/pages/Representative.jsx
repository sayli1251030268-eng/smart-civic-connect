import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { StatusChip } from '../components';
import { CATS, timeAgo } from '../lib';
import { UpdateCard } from './Updates.jsx';

function Escalate({ c }) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState('');
  const [msg, setMsg] = useState('');
  const send = async (e) => {
    e.preventDefault();
    try { await api(`/complaints/${c.id}/escalate`, { method: 'POST', body: { note } }); setMsg('Sent to the municipal office.'); setOpen(false); setNote(''); }
    catch (x) { setMsg(x.message); }
  };
  return (
    <div className="mt-2">
      <div className="flex flex-wrap items-center gap-2">
        <Link to={`/issues/${c.id}`} className="btn btn-ghost !py-1">Open and reply</Link>
        <button onClick={() => setOpen(!open)} className="btn btn-ghost !py-1">Escalate</button>
        {msg && <span role="status" className="text-sm text-slate-600">{msg}</span>}
      </div>
      {open && (
        <form onSubmit={send} className="mt-2 flex gap-2">
          <input required minLength={3} maxLength={500} className="field" placeholder="Why does this need urgent attention?" value={note} onChange={(e) => setNote(e.target.value)} />
          <button className="btn btn-primary">Send</button>
        </form>
      )}
    </div>
  );
}

export default function Representative() {
  const { user, ready } = useAuth();
  const isRep = user?.role === 'representative';
  const [tab, setTab] = useState('complaints');
  const [items, setItems] = useState(null);
  const [mine, setMine] = useState([]);
  const [f, setF] = useState({ title: '', body: '', ward: '' });
  const [before, setBefore] = useState(null);
  const [after, setAfter] = useState(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  const loadMine = () => api('/updates?limit=100').then((u) => setMine(u.filter((x) => x.author.id === user.id)));
  useEffect(() => {
    if (!isRep) return;
    setF((x) => ({ ...x, ward: user.ward || '' }));
    api(`/complaints?feed=trending&limit=100${user.ward ? `&ward=${encodeURIComponent(user.ward)}` : ''}`).then(setItems).catch((e) => setErr(e.message));
    loadMine();
  }, [isRep]);

  if (!ready) return null;
  if (!isRep) return <Navigate to="/" replace />;

  const post = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true);
    const fd = new FormData();
    Object.entries(f).forEach(([k, v]) => fd.append(k, v));
    if (before) fd.append('before_image', before);
    if (after) fd.append('after_image', after);
    try {
      await api('/updates', { method: 'POST', form: fd });
      setF({ ...f, title: '', body: '' }); setBefore(null); setAfter(null); e.target.reset();
      await loadMine(); setTab('mine');
    } catch (x) { setErr(x.message); } finally { setBusy(false); }
  };
  const remove = async (id) => { await api(`/updates/${id}`, { method: 'DELETE' }); loadMine(); };
  const tabBtn = (k, label) => (
    <button key={k} onClick={() => setTab(k)} className={`-mb-px whitespace-nowrap border-b-2 px-4 py-2 text-sm ${tab === k ? 'border-ink font-bold' : 'border-transparent text-slate-600'}`}>{label}</button>
  );

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div>
        <h1 className="text-3xl font-bold">Representative portal</h1>
        <p className="text-slate-600">{user.name}{user.ward && `, ${user.ward}`}</p>
      </div>
      {!user.is_verified && (
        <p role="status" className="rounded-xl border-2 border-signal bg-yellow-50 p-4 text-sm">
          Your account is waiting for verification by municipal staff. Until then you can read and comment, but you cannot post updates or escalate issues.
        </p>
      )}
      <div className="flex gap-1 overflow-x-auto border-b border-slate-300">
        {tabBtn('complaints', user.ward ? `Complaints in ${user.ward}` : 'All complaints')}
        {tabBtn('post', 'Post an update')}
        {tabBtn('mine', `My updates (${mine.length})`)}
      </div>
      {err && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{err}</p>}

      {tab === 'complaints' && (
        <section className="space-y-3">
          <p className="text-sm text-slate-600">Most supported first. Only municipal staff change official status, so use Escalate to flag urgent issues to them.</p>
          {items === null && <p className="text-slate-500">Loading…</p>}
          {items?.length === 0 && <p className="rounded-2xl bg-white p-6 text-slate-600 ring-1 ring-slate-200">No complaints tagged with your ward yet. Citizens add a ward when they report an issue.</p>}
          {items?.map((c) => (
            <article key={c.id} className="rounded-2xl bg-white p-4 ring-1 ring-slate-200">
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <StatusChip status={c.status} /><span>{CATS[c.category]}</span><span>{timeAgo(c.created_at)}</span>
                <span className="ml-auto font-bold text-ink">{c.counts.supports} supporters</span>
              </div>
              <h2 className="mt-1 font-bold">#{c.id} {c.title}</h2>
              <p className="line-clamp-2 text-sm text-slate-600">{c.description}</p>
              <Escalate c={c} />
            </article>
          ))}
        </section>
      )}

      {tab === 'post' && (
        <form onSubmit={post} className="space-y-4 rounded-2xl bg-white p-5 ring-1 ring-slate-200">
          <label className="block text-sm font-medium">Title
            <input required maxLength={200} className="field mt-1" placeholder="Drainage line on Karve Road completed" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} />
          </label>
          <label className="block text-sm font-medium">What was done
            <textarea required rows={5} className="field mt-1" placeholder="Describe the work, the cost or timeline if known, and what is planned next." value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} />
          </label>
          <label className="block text-sm font-medium">Ward or area
            <input className="field mt-1" value={f.ward} onChange={(e) => setF({ ...f, ward: e.target.value })} />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            {[['Before photo', setBefore], ['After photo', setAfter]].map(([label, fn]) => (
              <label key={label} className="block text-sm font-medium">{label} <span className="font-normal text-slate-500">(optional)</span>
                <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => fn(e.target.files[0] || null)}
                  className="mt-1 block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-ink file:px-4 file:py-2 file:text-white" />
              </label>
            ))}
          </div>
          <button disabled={busy || !user.is_verified} className="btn btn-primary w-full">{busy ? 'Publishing…' : 'Publish update'}</button>
        </form>
      )}

      {tab === 'mine' && (
        <section className="space-y-4">
          {mine.length === 0 && <p className="rounded-2xl bg-white p-6 text-slate-600 ring-1 ring-slate-200">You have not posted any updates yet.</p>}
          {mine.map((u) => <UpdateCard key={u.id} u={u} onDelete={remove} />)}
        </section>
      )}
    </div>
  );
}
