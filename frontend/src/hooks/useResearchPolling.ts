'use client';
import { useEffect, useRef, useState } from 'react';
import { api, errorMessage } from '@/lib/api';
import type { ResearchStatus } from '@/types/api';

/** Polls the backend for REAL research progress every 2s while `active`. */
export function useResearchPolling(
  meetingId: number | null,
  active: boolean,
  onFinished: (s: ResearchStatus) => void,
) {
  const [status, setStatus] = useState<ResearchStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const finished = useRef(onFinished);

  useEffect(() => {
    finished.current = onFinished;
  });

  useEffect(() => {
    if (meetingId === null || !active) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      try {
        const s = await api.getStatus(meetingId);
        if (cancelled) return;
        setStatus(s);
        setError(null);
        if (s.status === 'ready' || s.status === 'failed') {
          finished.current(s);
          return;
        }
      } catch (e) {
        if (cancelled) return;
        setError(errorMessage(e)); // keep polling: the backend may just be restarting
      }
      timer = setTimeout(tick, 2000);
    };
    void tick();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [meetingId, active]);

  return { status, error };
}
