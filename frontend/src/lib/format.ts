import type { EvidenceLabel, Freshness, MeetingStatus } from '@/types/api';

/** 'YYYY-MM-DD' -> 'Nov 08, 2026'. Parsed by hand so the time zone can never shift the day. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return 'Not provided';
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
  if (!y || !m || !d) return iso;
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' });
}

/** 'HH:MM[:SS]' -> '10:30 AM' */
export function formatTime(t: string): string {
  const [h, m] = t.split(':').map(Number);
  if (Number.isNaN(h) || Number.isNaN(m)) return t;
  const suffix = h >= 12 ? 'PM' : 'AM';
  return `${String(h % 12 === 0 ? 12 : h % 12).padStart(2, '0')}:${String(m).padStart(2, '0')} ${suffix}`;
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString('en-US', { month: 'short', day: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export const STATUS_TEXT: Record<MeetingStatus, string> = {
  created: 'Research pending',
  researching: 'Researching…',
  ready: 'Briefing ready',
  failed: 'Research failed',
};

export const STATUS_STYLE: Record<MeetingStatus, string> = {
  created: 'bg-slate-100 text-slate-600',
  researching: 'bg-blue-50 text-blue-700',
  ready: 'bg-indigo-50 text-indigo-700',
  failed: 'bg-rose-50 text-rose-700',
};

export const EVIDENCE_TEXT: Record<EvidenceLabel, string> = {
  verified: 'Verified',
  partially_supported: 'Partially supported',
  needs_verification: 'Needs verification',
  potentially_outdated: 'Potentially outdated',
};

export const EVIDENCE_STYLE: Record<EvidenceLabel, string> = {
  verified: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  partially_supported: 'bg-amber-50 text-amber-700 border-amber-200',
  needs_verification: 'bg-rose-50 text-rose-700 border-rose-200',
  potentially_outdated: 'bg-orange-50 text-orange-700 border-orange-200',
};

export const FRESHNESS_TEXT: Record<Freshness, string> = {
  recent: 'Recent',
  potentially_outdated: 'Potentially outdated',
  unknown: 'Date unknown',
};

export const FRESHNESS_STYLE: Record<Freshness, string> = {
  recent: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  potentially_outdated: 'bg-orange-50 text-orange-700 border-orange-200',
  unknown: 'bg-slate-100 text-slate-600 border-slate-200',
};
