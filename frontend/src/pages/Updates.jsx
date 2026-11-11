import { useEffect, useState } from 'react';
import { api, media } from '../api';
import { timeAgo } from '../lib';

export function UpdateCard({ u, onDelete }) {
  return (
    <article className="space-y-3 rounded-2xl bg-white p-5 ring-1 ring-slate-200">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-bold">{u.author.name}</span>
        {u.author.verified && <span className="rounded bg-signal px-1.5 py-0.5 text-xs font-bold">Verified representative</span>}
        {u.ward && <span className="text-slate-500">{u.ward}</span>}
        <span className="ml-auto text-xs text-slate-500">{timeAgo(u.created_at)}</span>
      </div>
      <h2 className="text-xl font-bold">{u.title}</h2>
      <p className="whitespace-pre-line text-slate-700">{u.body}</p>
      {(u.before_image_url || u.after_image_url) && (
        <div className="grid gap-3 sm:grid-cols-2">
          {u.before_image_url && <figure><img src={media(u.before_image_url)} alt="Before the work" className="h-48 w-full rounded-lg object-cover" /><figcaption className="mt-1 text-sm text-slate-600">Before</figcaption></figure>}
          {u.after_image_url && <figure><img src={media(u.after_image_url)} alt="After the work" className="h-48 w-full rounded-lg object-cover" /><figcaption className="mt-1 text-sm text-slate-600">After</figcaption></figure>}
        </div>
      )}
      {onDelete && <button onClick={() => onDelete(u.id)} className="btn btn-ghost !py-1">Delete update</button>}
    </article>
  );
}

export default function Updates() {
  const [items, setItems] = useState(null);
  const [ward, setWard] = useState('');
  const [err, setErr] = useState('');
  useEffect(() => {
    const t = setTimeout(() => {
      api(`/updates${ward ? `?ward=${encodeURIComponent(ward)}` : ''}`).then(setItems).catch((e) => setErr(e.message));
    }, 250);
    return () => clearTimeout(t);
  }, [ward]);
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-3xl font-bold">Development updates</h1>
        <p className="text-slate-600">Work announced by verified local representatives, with photos from the ground.</p>
      </div>
      <input aria-label="Filter by ward" className="field" placeholder="Filter by ward or area, for example Kothrud" value={ward} onChange={(e) => setWard(e.target.value)} />
      {err && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{err}</p>}
      {items === null && !err && <p className="text-slate-500">Loading…</p>}
      {items?.length === 0 && <p className="rounded-2xl bg-white p-6 text-slate-600 ring-1 ring-slate-200">No updates {ward ? 'for this ward' : ''} yet.</p>}
      {items?.map((u) => <UpdateCard key={u.id} u={u} />)}
    </div>
  );
}
