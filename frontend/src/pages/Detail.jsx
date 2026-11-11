import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, media } from '../api';
import { useAuth } from '../auth';
import { useTranslation } from '../i18n';
import { ComplaintCard, MapView, StatusRail, AbuseReportModal } from '../components';
import { STATUS, timeAgo, slaLabel } from '../lib';

export default function Detail() {
  const { id } = useParams();
  const { user } = useAuth();
  const { t } = useTranslation();
  const [c, setC] = useState(null);
  const [comments, setComments] = useState([]);
  const [text, setText] = useState('');
  const [err, setErr] = useState('');

  // Verification state
  const [rating, setRating] = useState(5);
  const [verifNote, setVerifNote] = useState('');
  const [verifBusy, setVerifBusy] = useState(false);

  // Abuse modal state
  const [abuseTarget, setAbuseTarget] = useState(null);

  // Citizen Receipt modal state
  const [receipt, setReceipt] = useState(null);
  const [showReceipt, setShowReceipt] = useState(false);

  const load = () =>
    Promise.all([api(`/complaints/${id}`), api(`/complaints/${id}/comments`)])
      .then(([d, cm]) => {
        setC(d);
        setComments(cm);
      })
      .catch((e) => setErr(e.message));

  useEffect(() => {
    load();
  }, [id, user]);

  const loadReceipt = async () => {
    try {
      const res = await api(`/complaints/${id}/receipt`);
      setReceipt(res);
      setShowReceipt(true);
    } catch (e) {
      alert(e.message);
    }
  };

  if (err && !c) return <p role="alert" className="rounded-lg bg-red-50 p-4 text-red-800">{err}</p>;
  if (!c) return <p className="text-slate-500 py-12 text-center">Loading complaint details…</p>;

  const post = async (e) => {
    e.preventDefault();
    try {
      await api(`/complaints/${id}/comments`, { method: 'POST', body: { body: text } });
      setText('');
      load();
    } catch (x) {
      setErr(x.message);
    }
  };

  const handleVerify = async (accepted) => {
    setVerifBusy(true);
    let coords = {};
    if (navigator.geolocation) {
      try {
        const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, { timeout: 3000 }));
        coords = { latitude: pos.coords.latitude, longitude: pos.coords.longitude };
      } catch {
        /* Optional geo check */
      }
    }
    try {
      await api(`/complaints/${id}/verify`, {
        method: 'POST',
        body: {
          accepted,
          rating: accepted ? rating : 1,
          note: verifNote,
          ...coords
        }
      });
      setErr('');
      load();
    } catch (x) {
      setErr(x.message);
    } finally {
      setVerifBusy(false);
    }
  };

  const sla = slaLabel(c.sla_hours_remaining, c.is_overdue);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link to="/" className="text-sm font-semibold text-slate-600 hover:text-ink">← Back to Issues</Link>
        <div className="flex items-center gap-2">
          <button onClick={loadReceipt} className="btn btn-ghost text-xs font-semibold !py-1.5 border border-slate-300">
            📄 Citizen Receipt & Audit
          </button>
          <button
            onClick={() => {
              const text = encodeURIComponent(`🚨 Civic Issue #${c.id}: "${c.title}". Please support it on Smart Civic Connect: ${window.location.href}`);
              window.open(`https://wa.me/?text=${text}`, '_blank');
            }}
            className="btn !bg-emerald-600 text-white text-xs font-semibold !py-1.5 hover:!bg-emerald-700"
          >
            📲 WhatsApp Share
          </button>
        </div>
      </div>

      <ComplaintCard c={c} onChange={(u) => setC({ ...c, ...u })} />

      {/* Progress & Department Section */}
      <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <h2 className="font-bold text-lg">Resolution Lifecycle</h2>
            {c.department ? (
              <p className="text-xs text-slate-600">Assigned Department: <span className="font-semibold text-ink">{c.department}</span></p>
            ) : (
              <p className="text-xs text-amber-700">Pending department allocation by Municipal Officer</p>
            )}
          </div>
          {sla && (
            <span className={`rounded-full border px-3 py-1 text-xs font-bold ${sla.cls}`}>
              {sla.label}
            </span>
          )}
        </div>

        <StatusRail status={c.status} />

        <ul className="mt-4 space-y-2 border-t border-slate-100 pt-4 text-sm">
          {[...c.history].reverse().map((h, i) => (
            <li key={i} className="flex gap-3 text-xs sm:text-sm">
              <span className="w-28 shrink-0 text-slate-500 font-mono">{timeAgo(h.at)}</span>
              <span>
                <b className="text-slate-800">{STATUS[h.status]?.label || h.status}</b>
                {h.note && <span className="text-slate-600 font-normal"> — {h.note}</span>}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {/* Before and After Repair Evidence */}
      {c.after_image_url && (
        <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200 shadow-sm space-y-4">
          <h2 className="font-bold text-lg">Official Repair Verification Evidence</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {c.image_url && (
              <figure className="overflow-hidden rounded-xl bg-slate-100 ring-1 ring-slate-200">
                <img src={media(c.image_url)} alt="Original reported issue" className="h-52 w-full object-cover" />
                <figcaption className="p-2 text-xs font-semibold text-slate-700 bg-white">1. Reported Photo</figcaption>
              </figure>
            )}
            <figure className="overflow-hidden rounded-xl bg-slate-100 ring-1 ring-slate-200">
              <img src={media(c.after_image_url)} alt="Municipal completion proof" className="h-52 w-full object-cover" />
              <figcaption className="p-2 text-xs font-semibold text-emerald-800 bg-emerald-50">
                2. Municipal After-Work Proof
              </figcaption>
            </figure>
          </div>

          {/* Citizen Verification Panel */}
          {c.status === 'resolved_awaiting_verification' && user && (
            <div className="mt-4 rounded-xl border-2 border-teal-500 bg-teal-50 p-5 space-y-4">
              <div>
                <h3 className="font-bold text-teal-900 text-base">Verify Work Quality as a Resident</h3>
                <p className="text-xs text-teal-800 mt-0.5">
                  The municipal department reported this issue resolved. As a local resident or supporter, please verify whether the fix is satisfactory.
                </p>
              </div>

              {/* 5-Star Rating Input */}
              <div>
                <label className="block text-xs font-bold text-teal-900 mb-1">Rate the Resolution Quality:</label>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setRating(star)}
                      className="text-2xl transition hover:scale-110"
                    >
                      {star <= rating ? '⭐' : '☆'}
                    </button>
                  ))}
                  <span className="ml-2 text-xs font-bold text-teal-800">({rating} of 5 Stars)</span>
                </div>
              </div>

              <textarea
                rows={2}
                className="field bg-white text-xs"
                placeholder="Add citizen feedback note (e.g. Cleanly asphalted, debris cleared)..."
                value={verifNote}
                onChange={(e) => setVerifNote(e.target.value)}
              />

              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  disabled={verifBusy}
                  onClick={() => handleVerify(true)}
                  className="btn !bg-emerald-600 text-white font-bold hover:!bg-emerald-700"
                >
                  ✓ Confirm & Accept Fix
                </button>
                <button
                  disabled={verifBusy}
                  onClick={() => handleVerify(false)}
                  className="btn btn-ghost text-red-700 hover:bg-red-50 font-bold"
                >
                  ✗ Reject (Still Broken)
                </button>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Citizen Verifications History */}
      {c.verifications_list?.length > 0 && (
        <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200 shadow-sm">
          <h2 className="mb-3 font-bold text-base">Citizen Verification Audit ({c.verifications_list.length})</h2>
          <ul className="space-y-3 divide-y divide-slate-100">
            {c.verifications_list.map((v) => (
              <li key={v.id} className="pt-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-800">{v.user_name}</span>
                  <span className="font-semibold text-amber-600">{'⭐'.repeat(v.rating)}</span>
                </div>
                {v.note && <p className="mt-1 text-slate-600">{v.note}</p>}
                <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-400">
                  <span>{timeAgo(v.created_at)}</span>
                  {v.photo_distance_m != null && <span>• Verified within {v.photo_distance_m}m of site</span>}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Location Map */}
      <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200 shadow-sm space-y-2">
        <h2 className="font-bold text-base">Exact GPS Location</h2>
        <MapView items={[c]} center={[c.latitude, c.longitude]} className="h-60" />
        {c.address && <p className="text-xs text-slate-600">Landmark: <span className="font-medium text-ink">{c.address}</span></p>}
      </section>

      {/* Community Discussion */}
      <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200 shadow-sm space-y-4">
        <h2 className="font-bold text-base">Community Discussion ({comments.length})</h2>
        <ul className="space-y-3">
          {comments.map((m) => (
            <li key={m.id} className="text-sm rounded-lg bg-slate-50 p-3 ring-1 ring-slate-100">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-bold text-slate-900">{m.author.name}</span>
                  {m.author.role === 'representative' && m.author.verified && (
                    <span className="ml-2 rounded bg-signal px-1.5 py-0.5 text-xs font-bold text-ink">
                      Verified Ward Representative
                    </span>
                  )}
                  <span className="ml-2 text-xs text-slate-500">{timeAgo(m.created_at)}</span>
                </div>
                {user && (
                  <button
                    onClick={() => setAbuseTarget({ type: 'comment', id: m.id })}
                    className="text-xs text-slate-400 hover:text-red-600"
                    title="Report comment"
                  >
                    🚩
                  </button>
                )}
              </div>
              <p className="mt-1 text-slate-700 leading-relaxed">{m.body}</p>
            </li>
          ))}
          {comments.length === 0 && (
            <li className="text-sm text-slate-500 italic py-2">
              No comments yet. Add details or photos to help municipal crews resolve this.
            </li>
          )}
        </ul>

        {user ? (
          <form onSubmit={post} className="flex gap-2 pt-2">
            <input
              required
              maxLength={1000}
              className="field"
              placeholder="Add your comment or ground update..."
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <button className="btn btn-primary font-semibold">Post</button>
          </form>
        ) : (
          <p className="text-xs text-slate-600 bg-slate-100 p-3 rounded-lg text-center">
            <Link to="/login" className="font-bold underline text-ink">Log in</Link> to participate in the community discussion.
          </p>
        )}
      </section>

      {/* Abuse Report Modal */}
      {abuseTarget && (
        <AbuseReportModal
          targetType={abuseTarget.type}
          targetId={abuseTarget.id}
          onClose={() => setAbuseTarget(null)}
        />
      )}

      {/* Official Citizen Receipt Modal */}
      {showReceipt && receipt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl ring-1 ring-slate-200">
            <div className="border-b-2 border-ink pb-3 flex items-center justify-between">
              <div>
                <h3 className="text-xl font-black text-ink">SMART CIVIC CONNECT</h3>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Official Citizen Complaint Receipt</p>
              </div>
              <span className="rounded bg-signal px-2 py-1 text-xs font-mono font-bold text-ink">{receipt.tracking_reference}</span>
            </div>

            <div className="mt-4 space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Complaint Title:</span>
                <span className="font-bold text-slate-800 text-right">{receipt.title}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Category:</span>
                <span className="font-bold text-slate-800 capitalize">{receipt.category}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Ward / Zone:</span>
                <span className="font-bold text-slate-800">{receipt.ward}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Handling Department:</span>
                <span className="font-bold text-slate-800">{receipt.department}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Official Status:</span>
                <span className="font-bold text-emerald-700 capitalize">{receipt.status.replace(/_/g, ' ')}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">SLA Commitment:</span>
                <span className="font-mono text-slate-700">{new Date(receipt.sla_deadline).toLocaleDateString()}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Digital Audit Stamp:</span>
                <span className="font-mono text-[10px] text-slate-600">{receipt.digital_stamp}</span>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button onClick={() => window.print()} className="btn btn-primary text-xs">🖨️ Print Receipt</button>
              <button onClick={() => setShowReceipt(false)} className="btn btn-ghost text-xs">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
