'use client';
import { useState } from 'react';
import Link from 'next/link';
import { Building2, ChevronLeft, ChevronRight, Download, Plus, Search, Trash2 } from 'lucide-react';
import PageShell from '@/components/layout/PageShell';
import { StatusPill } from '@/components/ui/Badges';
import { EmptyState, ErrorBanner, Spinner } from '@/components/ui/States';
import { useAsync } from '@/hooks/useAsync';
import { useDebounced } from '@/hooks/useDebounced';
import { api, errorMessage, saveBlob } from '@/lib/api';
import { formatDate, formatTime } from '@/lib/format';
import type { HistoryItem, MeetingStatus } from '@/types/api';

const PAGE_SIZE = 8;
type Sort = 'date_desc' | 'date_asc' | 'created_desc';

const field = 'rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20';

export default function HistoryView() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<MeetingStatus | ''>('');
  const [sort, setSort] = useState<Sort>('date_desc');
  const [offset, setOffset] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const q = useDebounced(search.trim(), 300);
  const key = `${q}|${status}|${sort}|${offset}`;
  const list = useAsync(() => api.listHistory({ q, status, sort, limit: PAGE_SIZE, offset }), key);

  const total = list.data?.total ?? 0;
  const items = list.data?.items ?? [];
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + PAGE_SIZE, total);

  const remove = async (m: HistoryItem) => {
    if (!window.confirm(`Delete the meeting with ${m.organization_or_person} and its briefing?`)) return;
    setBusyId(m.id);
    setActionError(null);
    try {
      await api.deleteMeeting(m.id);
      if (items.length === 1 && offset > 0) setOffset(offset - PAGE_SIZE);
      else list.reload();
    } catch (e) {
      setActionError(errorMessage(e));
    } finally {
      setBusyId(null);
    }
  };

  const pdf = async (m: HistoryItem) => {
    setBusyId(m.id);
    setActionError(null);
    try {
      const { blob, filename } = await api.downloadPdf(m.id);
      saveBlob(blob, filename);
    } catch (e) {
      setActionError(errorMessage(e));
    } finally {
      setBusyId(null);
    }
  };

  const filtered = q !== '' || status !== '';

  return (
    <PageShell>
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Briefing History</h1>
            <p className="mt-1 text-slate-500">Every meeting and briefing you&apos;ve created.</p>
          </div>
          <Link href="/new-briefing" className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700">
            <Plus size={18} /> New Meeting
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
          <div className="relative sm:col-span-2">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              aria-label="Search meetings"
              placeholder="Search company, attendee or purpose…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
              className={`${field} w-full pl-9`}
            />
          </div>
          <select aria-label="Filter by status" value={status} onChange={(e) => { setStatus(e.target.value as MeetingStatus | ''); setOffset(0); }} className={field}>
            <option value="">All statuses</option>
            <option value="ready">Briefing ready</option>
            <option value="created">Research pending</option>
            <option value="researching">Researching</option>
            <option value="failed">Failed</option>
          </select>
          <select aria-label="Sort" value={sort} onChange={(e) => { setSort(e.target.value as Sort); setOffset(0); }} className={field}>
            <option value="date_desc">Meeting date: newest</option>
            <option value="date_asc">Meeting date: oldest</option>
            <option value="created_desc">Recently created</option>
          </select>
        </div>

        {actionError && <ErrorBanner message={actionError} />}
        {list.error && <ErrorBanner message={list.error} onRetry={list.reload} />}

        {!list.error && !list.data && <Spinner label="Loading history…" />}

        {list.data && items.length === 0 && (
          filtered ? (
            <EmptyState title="No matching meetings" description="Try a different search or clear the filters." />
          ) : (
            <EmptyState
              title="No meetings yet"
              description="Create your first meeting and MeetWise AI will research it and prepare your briefing."
              action={<Link href="/new-briefing" className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700">Create a meeting</Link>}
            />
          )
        )}

        <div className="space-y-4">
          {items.map((m) => (
            <div key={m.id} className="flex flex-col gap-4 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition hover:border-indigo-200 sm:flex-row sm:items-center sm:justify-between">
              <Link href={`/meetings/${m.id}`} className="flex min-w-0 items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600"><Building2 size={22} /></div>
                <div className="min-w-0">
                  <h4 className="truncate text-base font-semibold text-slate-900">{m.organization_or_person}</h4>
                  <p className="mt-0.5 truncate text-sm text-slate-500">{m.purpose}</p>
                  <p className="mt-0.5 text-xs text-slate-400">
                    {formatDate(m.meeting_date)} · {formatTime(m.meeting_time)}
                    {m.attendee_name ? ` · ${m.attendee_name}` : ''}
                    {m.has_briefing ? ` · ${m.source_count} sources` : ''}
                  </p>
                </div>
              </Link>
              <div className="flex shrink-0 items-center gap-2">
                <StatusPill status={m.status} />
                {m.has_briefing && (
                  <button onClick={() => pdf(m)} disabled={busyId === m.id} aria-label={`Download PDF for ${m.organization_or_person}`} className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 disabled:opacity-50">
                    <Download size={16} />
                  </button>
                )}
                <button onClick={() => remove(m)} disabled={busyId === m.id} aria-label={`Delete meeting with ${m.organization_or_person}`} className="rounded-lg border border-slate-200 p-2 text-rose-600 hover:bg-rose-50 disabled:opacity-50">
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>

        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between text-sm text-slate-500">
            <span>Showing {from}–{to} of {total}</span>
            <div className="flex gap-2">
              <button onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0} className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 disabled:opacity-40"><ChevronLeft size={16} /> Prev</button>
              <button onClick={() => setOffset(offset + PAGE_SIZE)} disabled={to >= total} className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 disabled:opacity-40">Next <ChevronRight size={16} /></button>
            </div>
          </div>
        )}
      </div>
    </PageShell>
  );
}
