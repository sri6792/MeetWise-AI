'use client';
import { useState } from 'react';
import Link from 'next/link';
import { ExternalLink, ShieldCheck } from 'lucide-react';
import PageShell from '@/components/layout/PageShell';
import { FreshnessBadge } from '@/components/ui/Badges';
import { EmptyState, ErrorBanner, Spinner } from '@/components/ui/States';
import { useAsync } from '@/hooks/useAsync';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/format';
import type { Freshness, SourceCategory } from '@/types/api';

const field = 'rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20';

/** Research page = evidence explorer: every retrieved source for a chosen briefing. */
export default function EvidenceExplorer() {
  const [chosen, setChosen] = useState<number | null>(null);
  const [category, setCategory] = useState<SourceCategory | ''>('');
  const [freshness, setFreshness] = useState<Freshness | ''>('');

  const meetings = useAsync(() => api.listHistory({ status: 'ready', limit: 100 }), 'ready-meetings');
  const items = meetings.data?.items ?? [];
  const selected = chosen ?? items[0]?.id ?? null;

  const sourcesQ = useAsync(selected ? () => api.getSources(selected) : null, `sources-${selected ?? ''}`);
  const all = sourcesQ.data ?? [];
  const shown = all.filter((s) => (!category || s.category === category) && (!freshness || s.freshness === freshness));

  const count = (f: Freshness) => all.filter((s) => s.freshness === f).length;

  return (
    <PageShell>
      <div className="mx-auto max-w-5xl space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Research &amp; Evidence</h1>
          <p className="mt-1 text-slate-500">Inspect every source behind a briefing: where it came from, when it was published and how fresh it is.</p>
        </div>

        {meetings.error && <ErrorBanner message={meetings.error} onRetry={meetings.reload} />}
        {!meetings.data && !meetings.error && <Spinner />}

        {meetings.data && items.length === 0 && (
          <EmptyState
            title="No research to explore yet"
            description="Once a briefing has been generated, its sources appear here."
            action={<Link href="/new-briefing" className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700">Create a meeting</Link>}
          />
        )}

        {items.length > 0 && (
          <>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <select aria-label="Choose meeting" value={selected ?? ''} onChange={(e) => setChosen(Number(e.target.value))} className={`${field} sm:col-span-1`}>
                {items.map((m) => (
                  <option key={m.id} value={m.id}>{m.organization_or_person} · {formatDate(m.meeting_date)}</option>
                ))}
              </select>
              <select aria-label="Filter by type" value={category} onChange={(e) => setCategory(e.target.value as SourceCategory | '')} className={field}>
                <option value="">All source types</option>
                <option value="news">News</option>
                <option value="company">Company</option>
                <option value="person">Person</option>
              </select>
              <select aria-label="Filter by freshness" value={freshness} onChange={(e) => setFreshness(e.target.value as Freshness | '')} className={field}>
                <option value="">Any freshness</option>
                <option value="recent">Recent</option>
                <option value="potentially_outdated">Potentially outdated</option>
                <option value="unknown">Date unknown</option>
              </select>
            </div>

            {sourcesQ.error && <ErrorBanner message={sourcesQ.error} onRetry={sourcesQ.reload} />}
            {sourcesQ.loading && !sourcesQ.data && <Spinner label="Loading sources…" />}

            {sourcesQ.data && (
              <>
                <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
                  <ShieldCheck className="h-5 w-5 text-emerald-600" />
                  <span><strong>{all.length}</strong> sources</span>
                  <span className="text-emerald-700">{count('recent')} recent</span>
                  <span className="text-orange-700">{count('potentially_outdated')} potentially outdated</span>
                  <span className="text-slate-500">{count('unknown')} date unknown</span>
                  {selected && <Link href={`/meetings/${selected}`} className="ml-auto font-semibold text-indigo-600">Open briefing →</Link>}
                </div>

                {shown.length === 0 && <EmptyState title="No sources match these filters" />}

                <ol className="space-y-3">
                  {shown.map((s) => (
                    <li key={s.id} className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-bold text-indigo-600">[{s.ref}]</span>
                        <FreshnessBadge freshness={s.freshness} />
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] capitalize text-slate-500">{s.category}</span>
                      </div>
                      <a href={s.url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex items-center gap-1 text-base font-semibold text-slate-900 hover:text-indigo-700">
                        {s.title} <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                      <p className="break-all text-xs text-slate-400">{s.url}</p>
                      {s.snippet && <p className="mt-2 text-sm text-slate-600">{s.snippet}</p>}
                      <p className="mt-2 text-xs text-slate-500">Published: {formatDate(s.published_date)} · Retrieved: {formatDate(s.retrieved_at)}</p>
                    </li>
                  ))}
                </ol>
              </>
            )}
          </>
        )}
      </div>
    </PageShell>
  );
}
