'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage } from '@/lib/api';

/**
 * Runs `fn` whenever `key` changes (or reload() is called). Pass fn = null to wait.
 * `data` keeps the previous result while a new request is in flight (smoother lists).
 */
export function useAsync<T>(fn: (() => Promise<T>) | null, key: string) {
  const [tick, setTick] = useState(0);
  const requestKey = `${key}#${tick}`;
  const [result, setResult] = useState<{ key: string; data: T | null; error: string | null } | null>(null);
  const fnRef = useRef(fn);

  useEffect(() => {
    fnRef.current = fn;
  });

  useEffect(() => {
    const run = fnRef.current;
    if (!run) return;
    let cancelled = false;
    run()
      .then((data) => {
        if (!cancelled) setResult({ key: requestKey, data, error: null });
      })
      .catch((e: unknown) => {
        if (!cancelled) setResult({ key: requestKey, data: null, error: errorMessage(e) });
      });
    return () => {
      cancelled = true;
    };
  }, [requestKey]);

  const current = result?.key === requestKey;
  return {
    data: result?.data ?? null,
    error: current ? result.error : null,
    loading: fn !== null && !current,
    reload: useCallback(() => setTick((t) => t + 1), []),
  };
}
