import type { EvidenceLabel, Freshness, MeetingStatus } from '@/types/api';
import {
  EVIDENCE_STYLE, EVIDENCE_TEXT, FRESHNESS_STYLE, FRESHNESS_TEXT, STATUS_STYLE, STATUS_TEXT,
} from '@/lib/format';

export function EvidenceBadge({ label }: { label: EvidenceLabel }) {
  return (
    <span className={`inline-block rounded-full border px-2 py-0.5 text-[11px] font-semibold ${EVIDENCE_STYLE[label]}`}>
      {EVIDENCE_TEXT[label]}
    </span>
  );
}

export function FreshnessBadge({ freshness }: { freshness: Freshness }) {
  return (
    <span className={`inline-block rounded-full border px-2 py-0.5 text-[11px] font-semibold ${FRESHNESS_STYLE[freshness]}`}>
      {FRESHNESS_TEXT[freshness]}
    </span>
  );
}

export function StatusPill({ status }: { status: MeetingStatus }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_STYLE[status]}`}>
      {STATUS_TEXT[status]}
    </span>
  );
}
