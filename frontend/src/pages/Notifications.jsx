import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { timeAgo } from '../lib';

export default function Notifications() {
  const [items, setItems] = useState(null);
  useEffect(() => {
    api('/notifications').then((n) => { setItems(n); if (n.some((x) => !x.is_read)) api('/notifications/read', { method: 'POST' }); });
  }, []);
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-4 text-3xl font-bold">Updates on your issues</h1>
      {items === null && <p className="text-slate-500">Loading…</p>}
      {items?.length === 0 && <p className="rounded-2xl bg-white p-6 text-slate-600 ring-1 ring-slate-200">Nothing yet. You will see status changes and comments on the issues you report or support.</p>}
      <ul className="space-y-2">
        {items?.map((n) => (
          <li key={n.id}>
            <Link to={`/issues/${n.complaint_id}`} className={`flex items-center gap-3 rounded-xl bg-white p-3 ring-1 ring-slate-200 hover:bg-slate-50 ${n.is_read ? '' : 'border-l-4 border-signal'}`}>
              <span className="mr-auto text-sm">{n.message}</span>
              <span className="text-xs text-slate-500">{timeAgo(n.created_at)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
