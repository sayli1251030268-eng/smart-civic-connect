export const STATUS = {
  reported: { label: 'Reported', short: 'Reported', cls: 'bg-slate-200 text-slate-800', color: '#64748b' },
  under_review: { label: 'Under review', short: 'Review', cls: 'bg-blue-100 text-blue-900', color: '#2563eb' },
  assigned: { label: 'Assigned', short: 'Assigned', cls: 'bg-indigo-100 text-indigo-900', color: '#4f46e5' },
  in_progress: { label: 'In progress', short: 'Fixing', cls: 'bg-amber-100 text-amber-900', color: '#d97706' },
  resolved_awaiting_verification: { label: 'Fix awaiting verification', short: 'Check fix', cls: 'bg-teal-100 text-teal-900', color: '#0d9488' },
  verified_resolved: { label: 'Verified resolved', short: 'Resolved', cls: 'bg-emerald-100 text-emerald-900', color: '#059669' },
};

export const STEPS = Object.keys(STATUS);

export const CATS = {
  pothole: 'Pothole',
  garbage: 'Garbage',
  streetlight: 'Streetlight',
  water_leakage: 'Water leakage',
  drainage: 'Drainage',
  other: 'Other'
};

export const PUNE = [18.5204, 73.8567];

export function timeAgo(iso) {
  if (!iso) return '';
  const t = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
  const s = Math.max(1, (Date.now() - t) / 1000);
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

export const distLabel = (m) => (m == null ? null : m < 1000 ? `${m} m away` : `${(m / 1000).toFixed(1)} km away`);

export function slaLabel(hoursRemaining, isOverdue) {
  if (isOverdue) return { label: '🚨 SLA Overdue / Escalated', cls: 'bg-red-100 text-red-800 border-red-300' };
  if (hoursRemaining == null) return null;
  if (hoursRemaining <= 24) return { label: `⏱️ SLA: ${Math.round(hoursRemaining)}h left`, cls: 'bg-amber-100 text-amber-800 border-amber-300' };
  return { label: `⏱️ SLA: ${(hoursRemaining / 24).toFixed(1)}d left`, cls: 'bg-slate-100 text-slate-700 border-slate-200' };
}
