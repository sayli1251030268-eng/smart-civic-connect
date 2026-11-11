import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';

export default function Auth({ mode }) {
  const { login, register } = useAuth();
  const nav = useNavigate();
  const reg = mode === 'register';
  const [f, setF] = useState({ name: '', email: '', phone: '', password: '', role: 'citizen', ward: '' });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr('');
    try {
      const user = reg
        ? await register({ ...f, phone: f.phone || null, ward: f.ward || null })
        : await login({ email: f.email, password: f.password });
      nav(user.role === 'admin' ? '/admin' : user.role === 'representative' ? '/representative' : '/');
    } catch (x) {
      setErr(x.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-md">
      <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">{reg ? 'Create your account' : 'Welcome back'}</h1>
      <p className="mt-1 text-sm text-slate-600">
        {reg
          ? 'Report civic problems, back your neighbors, and track municipal verification.'
          : 'Log in to report and track civic progress.'}
      </p>

      <form onSubmit={submit} className="mt-6 space-y-4 rounded-2xl bg-white p-6 ring-1 ring-slate-200 shadow-sm">
        {reg && (
          <label className="block text-sm font-medium">
            Full Name
            <input required className="field mt-1" value={f.name} onChange={set('name')} />
          </label>
        )}

        <label className="block text-sm font-medium">
          Email Address
          <input required type="email" className="field mt-1" value={f.email} onChange={set('email')} />
        </label>

        {reg && (
          <label className="block text-sm font-medium">
            Mobile Number <span className="font-normal text-slate-400">(for WhatsApp / SMS updates)</span>
            <input
              type="tel"
              className="field mt-1"
              placeholder="+91 9876543210"
              value={f.phone}
              onChange={set('phone')}
            />
          </label>
        )}

        <label className="block text-sm font-medium">
          Password
          <input
            required
            type="password"
            minLength={8}
            className="field mt-1"
            value={f.password}
            onChange={set('password')}
          />
          {reg && <span className="text-xs text-slate-500">At least 8 characters.</span>}
        </label>

        {reg && (
          <>
            <label className="block text-sm font-medium">
              Role
              <select className="field mt-1 font-medium" value={f.role} onChange={set('role')}>
                <option value="citizen">Citizen / Resident</option>
                <option value="representative">Local Representative (Nagarsevak / Corporator / MLA)</option>
              </select>
            </label>
            {f.role === 'representative' && (
              <label className="block text-sm font-medium">
                Ward or Constituency Name
                <input required className="field mt-1" placeholder="e.g. Ward 14 - Kothrud" value={f.ward} onChange={set('ward')} />
                <span className="text-xs text-slate-500">
                  Municipal administrators will verify your official credentials before activating your portal.
                </span>
              </label>
            )}
          </>
        )}

        {err && <p role="alert" className="rounded-lg bg-red-50 p-2.5 text-xs text-red-800">{err}</p>}

        <button disabled={busy} className="btn btn-primary w-full font-bold shadow">
          {busy ? 'Processing…' : reg ? 'Create Account' : 'Sign In'}
        </button>
      </form>

      <p className="mt-4 text-center text-sm text-slate-600">
        {reg ? 'Already registered? ' : 'New to Smart Civic Connect? '}
        <Link className="font-bold text-ink underline" to={reg ? '/login' : '/register'}>
          {reg ? 'Sign in' : 'Create an account'}
        </Link>
      </p>
    </div>
  );
}
