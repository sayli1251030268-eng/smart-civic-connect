const isDevPort = typeof window !== 'undefined' && window.location.port === '5173';
const BASE = import.meta.env.VITE_API_URL !== undefined
  ? import.meta.env.VITE_API_URL
  : (isDevPort ? 'http://localhost:8000' : '');

export const media = (u) => {
  if (!u) return null;
  if (u.startsWith('http')) return u;
  const prefix = BASE || (isDevPort ? 'http://localhost:8000' : '');
  return prefix + u;
};

export async function api(path, { method = 'GET', body, form } = {}) {
  const headers = {};
  const token = localStorage.getItem('token');
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body) headers['Content-Type'] = 'application/json';
  
  let res;
  try {
    const url = (BASE || '') + path;
    res = await fetch(url, {
      method,
      headers,
      body: form || (body ? JSON.stringify(body) : undefined)
    });
  } catch {
    throw Object.assign(new Error('Cannot reach the server. Check that the backend is running.'), { status: 0 });
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = typeof data.detail === 'string' ? data.detail : 'Please check the details you entered.';
    throw Object.assign(new Error(msg), { status: res.status, data });
  }
  return data;
}
