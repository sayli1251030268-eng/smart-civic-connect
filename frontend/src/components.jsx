import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap, useMapEvents } from 'react-leaflet';
import { api, media } from './api';
import { useAuth } from './auth';
import { useTranslation } from './i18n';
import { STATUS, STEPS, CATS, timeAgo, distLabel, slaLabel } from './lib';

export const StatusChip = ({ status }) => {
  const s = STATUS[status] || STATUS.reported;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${s.cls}`}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.color }} />
      {s.label}
    </span>
  );
};

export function StatusRail({ status }) {
  const i = STEPS.indexOf(status);
  return (
    <ol className="flex items-start" aria-label="Complaint progress">
      {STEPS.map((s, k) => (
        <li key={s} className="min-w-0 flex-1">
          <div className="flex items-center">
            <span
              className={`h-3 w-3 shrink-0 rounded-full ${k <= i ? 'bg-ink' : 'bg-slate-300'} ${k === i ? 'ring-4 ring-signal' : ''}`}
            />
            {k < STEPS.length - 1 && <span className={`h-0.5 flex-1 ${k < i ? 'bg-ink' : 'bg-slate-300'}`} />}
          </div>
          <p className={`mt-2 pr-1 text-[11px] leading-tight ${k === i ? 'font-bold' : 'text-slate-500'}`}>
            {STATUS[s].short}
          </p>
        </li>
      ))}
    </ol>
  );
}

export function AbuseReportModal({ targetType, targetId, onClose, onSuccess }) {
  const [reason, setReason] = useState('spam');
  const [details, setDetails] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr('');
    try {
      const path = targetType === 'complaint'
        ? `/complaints/${targetId}/report-abuse`
        : `/comments/${targetId}/report-abuse`;
      await api(path, {
        method: 'POST',
        body: { target_type: targetType, target_id: targetId, reason, details }
      });
      alert('Report submitted for moderation. Thank you for keeping the platform safe.');
      onSuccess?.();
      onClose();
    } catch (x) {
      setErr(x.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl ring-1 ring-slate-200">
        <h3 className="text-lg font-bold">Report Abuse or Misuse</h3>
        <p className="mt-1 text-xs text-slate-600">
          Our municipal moderation team reviews flagged reports to prevent spam, harassment, and false reports.
        </p>

        {err && <p className="mt-3 rounded-lg bg-red-50 p-2 text-xs text-red-800">{err}</p>}

        <form onSubmit={submit} className="mt-4 space-y-4">
          <label className="block text-sm font-medium">
            Reason
            <select className="field mt-1" value={reason} onChange={(e) => setReason(e.target.value)}>
              <option value="spam">Spam / Advertising</option>
              <option value="false_report">False or Fake Report</option>
              <option value="inappropriate">Offensive / Inappropriate Content</option>
              <option value="harassment">Harassment or Abuse</option>
              <option value="other">Other Violation</option>
            </select>
          </label>

          <label className="block text-sm font-medium">
            Additional Details <span className="text-xs text-slate-500">(optional)</span>
            <textarea
              rows={3}
              className="field mt-1"
              placeholder="Explain why this content should be reviewed..."
              value={details}
              onChange={(e) => setDetails(e.target.value)}
            />
          </label>

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn btn-ghost">Cancel</button>
            <button disabled={busy} className="btn bg-red-600 text-white hover:bg-red-700">
              {busy ? 'Submitting…' : 'Submit Report'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function ComplaintCard({ c, onChange }) {
  const { user } = useAuth();
  const { t } = useTranslation();
  const nav = useNavigate();
  const [showAbuseModal, setShowAbuseModal] = useState(false);

  const act = async (kind) => {
    if (!user) return nav('/login');
    try {
      onChange(await api(`/complaints/${c.id}/${kind}`, { method: 'POST' }));
    } catch (e) {
      alert(e.message);
    }
  };

  const toggleFollow = async () => {
    if (!user) return nav('/login');
    try {
      const res = await api(`/complaints/${c.id}/follow`, { method: 'POST' });
      onChange({
        ...c,
        me: { ...c.me, followed: res.following }
      });
    } catch (e) {
      alert(e.message);
    }
  };

  const shareWhatsApp = () => {
    const text = encodeURIComponent(`🚨 Civic Issue on Smart Civic Connect: "${c.title}" at ${c.address || c.ward || 'Pune'}.\nSupport this issue so authorities fix it quickly: ${window.location.origin}/issues/${c.id}`);
    window.open(`https://wa.me/?text=${text}`, '_blank');
  };

  const pill = (on) => `btn !px-3 ${on ? 'bg-ink text-white font-medium' : 'btn-ghost'}`;
  const sla = slaLabel(c.sla_hours_remaining, c.is_overdue);

  return (
    <article className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200 transition hover:shadow-md">
      {c.image_url && (
        <Link to={`/issues/${c.id}`} className="block relative">
          <img src={media(c.image_url)} alt={c.title} className="h-56 w-full object-cover" loading="lazy" />
          {c.is_escalated && (
            <span className="absolute top-3 left-3 rounded-full bg-red-600 px-3 py-1 text-xs font-bold text-white shadow">
              🚨 ESCALATED TO WARD
            </span>
          )}
          {c.counts.verifications > 0 && (
            <span className="absolute top-3 right-3 rounded-full bg-emerald-600 px-3 py-1 text-xs font-bold text-white shadow">
              ⭐ {c.rating} Verified
            </span>
          )}
        </Link>
      )}

      <div className="space-y-3 p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <StatusChip status={c.status} />
          {sla && (
            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${sla.cls}`}>
              {sla.label}
            </span>
          )}
          <span className="rounded bg-slate-100 px-2 py-0.5 font-medium text-slate-700">{CATS[c.category] || c.category}</span>
          <span>{c.author.name}, {timeAgo(c.created_at)}</span>
          {c.ward && <span className="font-semibold text-ink">📍 {c.ward}</span>}
          {c.distance_m != null && <span className="font-medium text-blue-700">{distLabel(c.distance_m)}</span>}
        </div>

        <Link to={`/issues/${c.id}`} className="block group">
          <h3 className="text-xl font-bold leading-snug group-hover:text-blue-700">{c.title}</h3>
          <p className="mt-1 line-clamp-2 text-sm text-slate-600 leading-relaxed">{c.description}</p>
        </Link>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-100">
          <button
            onClick={() => act('support')}
            className={c.me.supported ? 'btn bg-ink text-white font-semibold' : 'btn btn-primary font-semibold'}
          >
            {c.me.supported ? t('supporting_btn') : t('support_btn')} ({c.counts.supports})
          </button>

          <button onClick={() => act('like')} className={pill(c.me.liked)}>
            👍 {c.counts.likes}
          </button>

          <button onClick={() => act('repost')} className={pill(c.me.reposted)}>
            🔄 {c.counts.reposts}
          </button>

          <Link to={`/issues/${c.id}`} className="btn btn-ghost !px-3 text-slate-700">
            💬 {c.counts.comments}
          </Link>

          <button
            onClick={toggleFollow}
            className={`btn !px-3 text-xs ${c.me.followed ? 'bg-amber-100 text-amber-900 border border-amber-300' : 'btn-ghost'}`}
            title="Follow updates on this complaint"
          >
            {c.me.followed ? '★ Following' : '☆ Follow'}
          </button>

          <button
            onClick={shareWhatsApp}
            className="btn btn-ghost !px-2.5 text-emerald-700 hover:bg-emerald-50"
            title="Share on WhatsApp"
          >
            📲 Share
          </button>

          {user && (
            <button
              onClick={() => setShowAbuseModal(true)}
              className="ml-auto text-xs text-slate-400 hover:text-red-600"
              title="Report content abuse"
            >
              🚩
            </button>
          )}
        </div>
      </div>

      {showAbuseModal && (
        <AbuseReportModal
          targetType="complaint"
          targetId={c.id}
          onClose={() => setShowAbuseModal(false)}
        />
      )}
    </article>
  );
}

function Recenter({ center }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center);
  }, [center[0], center[1]]);
  return null;
}

function Picker({ onPick }) {
  useMapEvents({
    click: (e) => onPick([e.latlng.lat, e.latlng.lng]),
  });
  return null;
}

export function MapView({ items = [], center, onPick, picked, className = 'h-[420px]' }) {
  return (
    <MapContainer center={center} zoom={14} className={`${className} z-0 w-full rounded-2xl ring-1 ring-slate-200`}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Recenter center={center} />
      {onPick && <Picker onPick={onPick} />}
      {picked && (
        <CircleMarker
          center={picked}
          radius={11}
          pathOptions={{ color: '#14213D', fillColor: '#FFC93C', fillOpacity: 1, weight: 3 }}
        />
      )}
      {items.map((c) => {
        const s = STATUS[c.status] || STATUS.reported;
        return (
          <CircleMarker
            key={c.id}
            center={[c.latitude, c.longitude]}
            radius={8}
            pathOptions={{ color: '#fff', weight: 2, fillColor: s.color, fillOpacity: 0.95 }}
          >
            <Popup>
              <Link to={`/issues/${c.id}`} className="font-bold text-sm hover:underline">{c.title}</Link>
              <br />
              <span className="text-xs text-slate-600">{s.label} ({c.counts.supports} supports)</span>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
