import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { MapView } from '../components';
import { useTranslation } from '../i18n';
import { CATS, PUNE, distLabel } from '../lib';

export default function Report() {
  const nav = useNavigate();
  const { t } = useTranslation();
  const [f, setF] = useState({
    title: '',
    description: '',
    category: 'pothole',
    address: '',
    ward: '',
    is_anonymous: false
  });
  const [pos, setPos] = useState(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dups, setDups] = useState(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState(null);

  const set = (k) => (e) =>
    setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  const locate = () =>
    navigator.geolocation?.getCurrentPosition(
      (p) => {
        setPos([p.coords.latitude, p.coords.longitude]);
        setErr('');
      },
      () => setErr('We could not read your location. Tap the map to drop a pin instead.'),
      { enableHighAccuracy: true }
    );

  useEffect(() => {
    locate();
  }, []);

  const pickFile = async (e) => {
    const x = e.target.files[0];
    setFile(x || null);
    setPreview(x ? URL.createObjectURL(x) : null);
    setHint(null);
    if (!x) return;
    const fd = new FormData();
    fd.append('image', x);
    try {
      const r = await api('/ai/classify', { method: 'POST', form: fd });
      if (r.available) setHint(r);
    } catch {
      /* AI suggestions are optional fallback */
    }
  };

  const submit = async (force = false) => {
    if (!pos) return setErr('Set the issue location first: use your location or tap the map.');
    const fd = new FormData();
    Object.entries(f).forEach(([k, v]) => fd.append(k, v));
    fd.append('latitude', pos[0]);
    fd.append('longitude', pos[1]);
    fd.append('force', force);
    if (file) fd.append('image', file);
    setBusy(true);
    setErr('');
    try {
      const c = await api('/complaints', { method: 'POST', form: fd });
      nav(`/issues/${c.id}`);
    } catch (e) {
      if (e.status === 409) {
        setDups(e.data.suggestions);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        setErr(e.message);
      }
    } finally {
      setBusy(false);
    }
  };

  const support = async (id) => {
    try {
      await api(`/complaints/${id}/support`, { method: 'POST' });
      nav(`/issues/${id}`);
    } catch (e) {
      setErr(e.message);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">{t('report_issue')}</h1>
        <p className="mt-1 text-sm text-slate-600">
          A clear photo, exact pin, and description route your report directly to the responsible municipal department.
        </p>
      </div>

      {dups && (
        <section className="rounded-2xl border-2 border-signal bg-yellow-50 p-5 shadow-sm" aria-live="polite">
          <h2 className="font-bold text-slate-900 text-lg">⚠️ Similar Complaints Found Nearby</h2>
          <p className="mt-1 text-xs text-slate-700">
            Our AI detected identical or nearby reports. Supporting an existing report boosts its municipal priority rather than creating fragmented duplicates!
          </p>
          <ul className="mt-3 space-y-2">
            {dups.map((d) => (
              <li key={d.complaint_id} className="flex flex-wrap items-center gap-3 rounded-xl bg-white p-3 ring-1 ring-slate-200">
                <div className="mr-auto">
                  <Link to={`/issues/${d.complaint_id}`} className="font-bold text-sm text-blue-700 underline">
                    #{d.complaint_id} {d.title}
                  </Link>
                  <p className="text-xs text-slate-500">
                    {distLabel(d.distance_m)?.replace('away', 'from your pin')}
                    {d.image_similarity != null && ` • Visual similarity ${Math.round(d.image_similarity * 100)}%`}
                    {d.confidence === 'likely' ? ' • High confidence duplicate' : ' • Possible duplicate'}
                  </p>
                </div>
                <button type="button" onClick={() => support(d.complaint_id)} className="btn btn-primary text-xs font-semibold">
                  I Face This Too (Support)
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-3 pt-2 border-t border-yellow-200">
            <button
              type="button"
              onClick={() => submit(true)}
              disabled={busy}
              className="btn btn-ghost text-xs text-slate-700 hover:text-ink"
            >
              This is a distinct issue, file report anyway →
            </button>
          </div>
        </section>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setDups(null);
          submit(false);
        }}
        className="space-y-5 rounded-2xl bg-white p-6 ring-1 ring-slate-200 shadow-sm"
      >
        <label className="block text-sm font-medium">
          Category
          <select className="field mt-1 font-semibold" value={f.category} onChange={set('category')}>
            {Object.entries(CATS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </label>

        <label className="block text-sm font-medium">
          Issue Title
          <input
            required
            maxLength={200}
            className="field mt-1"
            placeholder="e.g. Deep crater pothole outside school gate"
            value={f.title}
            onChange={set('title')}
          />
        </label>

        <label className="block text-sm font-medium">
          Detailed Description
          <textarea
            required
            rows={4}
            className="field mt-1 leading-relaxed"
            placeholder="Describe the hazard: size, duration, public safety risks, water logging..."
            value={f.description}
            onChange={set('description')}
          />
        </label>

        <div>
          <p className="text-sm font-medium">Upload Photo</p>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={pickFile}
            className="mt-1 block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-ink file:px-4 file:py-2 file:text-white file:font-semibold"
          />
          {preview && (
            <div className="mt-3 overflow-hidden rounded-xl ring-1 ring-slate-200">
              <img src={preview} alt="Selected issue" className="h-44 w-full object-cover" />
            </div>
          )}
          {hint && hint.category !== f.category && hint.confidence >= 0.5 && (
            <div role="status" className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-yellow-50 p-3 text-xs ring-1 ring-signal">
              <span>
                🤖 AI Suggestion: Photo indicates a <b>{CATS[hint.category]}</b> issue ({Math.round(hint.confidence * 100)}% confidence).
              </span>
              <button
                type="button"
                onClick={() => setF({ ...f, category: hint.category })}
                className="btn btn-primary !py-1 text-xs"
              >
                Switch to {CATS[hint.category]}
              </button>
            </div>
          )}
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium">
              GPS Location{' '}
              {pos ? (
                <span className="font-mono text-xs text-slate-500">
                  ({pos[0].toFixed(5)}, {pos[1].toFixed(5)})
                </span>
              ) : (
                <span className="text-xs text-amber-700">Not set</span>
              )}
            </p>
            <button type="button" onClick={locate} className="btn btn-ghost !py-1 text-xs">
              📍 Use Current GPS
            </button>
          </div>
          <MapView center={pos || PUNE} picked={pos} onPick={setPos} className="h-60" />
          <p className="mt-1 text-xs text-slate-500">Tap anywhere on the map to place or adjust your issue pin.</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm font-medium">
            Landmark / Street Address <span className="font-normal text-slate-400">(optional)</span>
            <input
              className="field mt-1"
              placeholder="e.g. Opposite Petrol Pump, Paud Road"
              value={f.address}
              onChange={set('address')}
            />
          </label>

          <label className="block text-sm font-medium">
            Ward / Neighborhood <span className="font-normal text-slate-400">(optional)</span>
            <input
              className="field mt-1"
              placeholder="e.g. Kothrud, Ward 12"
              value={f.ward}
              onChange={set('ward')}
            />
          </label>
        </div>

        {/* Anonymous Reporting Option */}
        <label className="flex items-start gap-3 rounded-xl bg-slate-50 p-3 ring-1 ring-slate-200 cursor-pointer">
          <input
            type="checkbox"
            checked={f.is_anonymous}
            onChange={set('is_anonymous')}
            className="mt-0.5 h-4 w-4 rounded text-ink"
          />
          <div className="text-xs">
            <span className="font-bold text-slate-900">Report Anonymously</span>
            <p className="text-slate-600 mt-0.5">
              Your name will be masked as "Anonymous Resident" on public feeds to protect your privacy. Municipal authorities can still resolve your report.
            </p>
          </div>
        </label>

        {err && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{err}</p>}

        <button disabled={busy} className="btn btn-primary w-full font-bold shadow">
          {busy ? 'Scanning for duplicate complaints…' : 'Submit Civic Report'}
        </button>
      </form>
    </div>
  );
}
