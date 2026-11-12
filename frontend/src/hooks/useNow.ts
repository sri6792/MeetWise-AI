'use client';
import { useSyncExternalStore } from 'react';

const subscribe = () => () => {};

function snapshot(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}`;
}

/**
 * Local date + hour, available only in the browser (null while prerendering).
 * Uses useSyncExternalStore so no `new Date()` runs during prerender, which
 * Cache Components forbids, and there is no hydration mismatch.
 */
export function useNow(): { today: string; hour: number } | null {
  const s = useSyncExternalStore(subscribe, snapshot, () => '');
  if (!s) return null;
  return { today: s.slice(0, 10), hour: Number(s.slice(11)) };
}
