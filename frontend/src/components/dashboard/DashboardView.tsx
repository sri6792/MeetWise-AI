'use client';
import Link from 'next/link';
import {
  Search, Bell, Plus, CalendarDays, FileText, Clock, ArrowUpRight, Sparkles, Building2, MoreHorizontal,
} from 'lucide-react';
import PageShell from '@/components/layout/PageShell';
import { StatusPill } from '@/components/ui/Badges';
import { EmptyState, ErrorBanner } from '@/components/ui/States';
import { useAsync } from '@/hooks/useAsync';
import { useNow } from '@/hooks/useNow';
import { api } from '@/lib/api';
import { formatDate, formatTime } from '@/lib/format';

const pad = (n: number) => String(n).padStart(2, '0');

function greeting(hour: number) {
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

function longDate(iso: string) {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
}

export default function DashboardView() {
  const now = useNow();
  const today = now?.today;

  const data = useAsync(
    today ? async () => {
      const [stats, upcoming] = await Promise.all([
        api.getStats(today),
        api.listHistory({ date_from: today, sort: 'date_asc', limit: 5 }),
      ]);
      return { stats, upcoming: upcoming.items };
    } : null,
    `dashboard-${today ?? ''}`,
  );

  const stats = data.data?.stats;
  const meetings = data.data?.upcoming ?? [];
  const cards = [
    { title: 'Total Meetings', value: stats?.total_meetings, description: 'All meetings created', icon: CalendarDays, color: 'bg-indigo-50 text-indigo-600' },
    { title: 'Briefings Generated', value: stats?.briefings_ready, description: 'AI-powered reports', icon: FileText, color: 'bg-purple-50 text-purple-600' },
    { title: 'Upcoming Meetings', value: stats?.upcoming_meetings, description: 'Scheduled meetings', icon: Clock, color: 'bg-blue-50 text-blue-600' },
  ];

  return (
    <PageShell>
      {/* Header */}
      <header className="mb-9 flex items-center justify-between">
        <div>
          <p className="min-h-6 text-base text-slate-500">{now ? longDate(now.today) : ''}</p>

          <h1 className="mt-1 text-3xl font-bold text-slate-900">
            {now ? greeting(now.hour) : 'Welcome'}! 👋
          </h1>

          <p className="mt-1 text-base text-slate-500">
            Here&apos;s your meeting intelligence overview.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/history" aria-label="Search meetings" className="rounded-xl border border-slate-200 bg-white p-3 text-slate-500 hover:bg-slate-50">
            <Search size={20} />
          </Link>

          <span className="relative hidden rounded-xl border border-slate-200 bg-white p-3 text-slate-500 sm:block" aria-hidden="true">
            <Bell size={20} />
            {stats && stats.researching > 0 && <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-indigo-500" />}
          </span>

          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-base font-semibold text-indigo-700">
            S
          </div>
        </div>
      </header>

      {/* Welcome banner */}
      <section className="mb-8 overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-600 via-indigo-600 to-purple-600 p-7 text-white shadow-lg shadow-indigo-100">
        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
          <div>
            <div className="mb-3 flex items-center gap-2 text-indigo-100">
              <Sparkles size={19} />
              <span className="text-sm font-semibold uppercase tracking-widest">Your AI Meeting Assistant</span>
            </div>
            <h2 className="text-3xl font-bold">Walk into every meeting prepared.</h2>
            <p className="mt-2 max-w-xl text-base leading-7 text-indigo-100">
              Research companies, understand people and discover
              opportunities before your next important conversation.
            </p>
          </div>

          <Link
            href="/new-briefing"
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 text-base font-semibold text-indigo-700 shadow-sm transition hover:bg-indigo-50"
          >
            <Plus size={20} />
            Create New Briefing
          </Link>
        </div>
      </section>

      {data.error && <div className="mb-8"><ErrorBanner message={data.error} onRetry={data.reload} /></div>}

      {/* Statistics */}
      <section className="mb-8 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {cards.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.title} className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:shadow-md">
              <div className="flex items-center justify-between">
                <div className={`rounded-xl p-3 ${stat.color}`}><Icon size={22} /></div>
                <MoreHorizontal size={21} className="text-slate-400" />
              </div>
              <p className="mt-5 text-base text-slate-500">{stat.title}</p>
              <h3 className="mt-1 text-4xl font-bold text-slate-900">
                {stat.value === undefined ? '–' : pad(stat.value)}
              </h3>
              <p className="mt-2 text-sm text-slate-400">{stat.description}</p>
            </div>
          );
        })}
      </section>

      {/* Main content */}
      <section className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Meetings */}
        <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm xl:col-span-2">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-slate-900">Upcoming Meetings</h3>
              <p className="mt-1 text-sm text-slate-400">Your scheduled meetings</p>
            </div>
            <Link href="/history" className="text-sm font-semibold text-indigo-600 hover:text-indigo-800">View all</Link>
          </div>

          {!data.data && !data.error && <p className="py-8 text-center text-sm text-slate-400">Loading meetings…</p>}

          {data.data && meetings.length === 0 && (
            <EmptyState
              title="No upcoming meetings"
              description="Create a meeting and we'll research it for you."
              action={<Link href="/new-briefing" className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700">New meeting</Link>}
            />
          )}

          <div className="space-y-4">
            {meetings.map((meeting) => (
              <Link
                key={meeting.id}
                href={`/meetings/${meeting.id}`}
                className="flex flex-col gap-4 rounded-xl border border-slate-100 p-4 transition hover:border-indigo-200 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                    <Building2 size={22} />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-base font-semibold text-slate-900">{meeting.organization_or_person}</h4>
                    <p className="mt-1 truncate text-sm text-slate-500">{meeting.purpose}</p>
                  </div>
                </div>

                <div className="sm:text-right">
                  <p className="text-sm font-medium text-slate-700">{formatDate(meeting.meeting_date)}</p>
                  <p className="mt-1 text-sm text-slate-400">{formatTime(meeting.meeting_time)}</p>
                  <span className="mt-2 inline-block"><StatusPill status={meeting.status} /></span>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Quick actions */}
        <div className="space-y-5">
          <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm">
            <h3 className="text-xl font-bold text-slate-900">Quick Actions</h3>
            <p className="mt-1 text-sm text-slate-400">Get started with MeetWise AI</p>

            <div className="mt-5 space-y-3">
              <Link href="/new-briefing" className="flex items-center justify-between rounded-xl bg-indigo-50 p-4 transition hover:bg-indigo-100">
                <div className="flex items-center gap-3">
                  <Plus className="text-indigo-600" size={20} />
                  <span className="text-base font-semibold text-indigo-800">New Meeting</span>
                </div>
                <ArrowUpRight size={19} className="text-indigo-600" />
              </Link>

              <Link href="/history" className="flex items-center justify-between rounded-xl bg-slate-50 p-4 transition hover:bg-slate-100">
                <div className="flex items-center gap-3">
                  <FileText className="text-slate-600" size={20} />
                  <span className="text-base font-semibold text-slate-700">View Briefings</span>
                </div>
                <ArrowUpRight size={19} className="text-slate-500" />
              </Link>

              <Link href="/research" className="flex items-center justify-between rounded-xl bg-slate-50 p-4 transition hover:bg-slate-100">
                <div className="flex items-center gap-3">
                  <Search className="text-slate-600" size={20} />
                  <span className="text-base font-semibold text-slate-700">Explore Research</span>
                </div>
                <ArrowUpRight size={19} className="text-slate-500" />
              </Link>
            </div>
          </div>

          <div className="rounded-2xl border border-indigo-100 bg-indigo-50/70 p-5">
            <Sparkles className="mb-3 text-indigo-600" size={23} />
            <h3 className="text-lg font-bold text-slate-900">Smarter preparation</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Discover recent company developments and prepare
              meaningful questions before every meeting.
            </p>
          </div>
        </div>
      </section>

      <footer className="mt-10 border-t border-slate-200 py-5 text-center text-sm text-slate-400">
        MeetWise AI · Intelligent preparation for meaningful meetings
      </footer>
    </PageShell>
  );
}
