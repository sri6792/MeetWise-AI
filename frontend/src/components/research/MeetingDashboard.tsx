'use client';
import React, { useState } from 'react';
import Link from 'next/link';
import {
  Building2, User, Newspaper, ArrowLeft, ExternalLink, Lightbulb, HelpCircle, LayoutList, ShieldCheck,
  Calendar, Target, AlertTriangle,
} from 'lucide-react';
import type {
  AttendeeSection, BriefingResponse, CompanySection, Opportunity, QuestionItem, Questions, Statement,
} from '@/types/api';
import { EvidenceBadge, FreshnessBadge } from '@/components/ui/Badges';
import { formatDate, formatDateTime, formatTime } from '@/lib/format';

type Tab = 'overview' | 'company' | 'person' | 'opportunities' | 'questions';

const COMPANY_BLOCKS: { key: keyof CompanySection; title: string }[] = [
  { key: 'overview', title: 'Company overview' },
  { key: 'business_model', title: 'Business model' },
  { key: 'products_services', title: 'Products & services' },
  { key: 'strategic_initiatives', title: 'Strategic initiatives' },
  { key: 'competitors', title: 'Competitors' },
  { key: 'challenges', title: 'Potential challenges' },
];

const PERSON_BLOCKS: { key: keyof Omit<AttendeeSection, 'identity_note'>; title: string }[] = [
  { key: 'role', title: 'Current role' },
  { key: 'experience', title: 'Previous experience' },
  { key: 'achievements', title: 'Public achievements' },
  { key: 'expertise', title: 'Areas of expertise' },
  { key: 'public_content', title: 'Interviews & articles' },
];

const QUESTION_GROUPS: { key: keyof Questions; title: string }[] = [
  { key: 'strategic', title: 'Strategic' },
  { key: 'technical', title: 'Technical' },
  { key: 'business', title: 'Business' },
  { key: 'collaboration', title: 'Collaboration' },
  { key: 'follow_up', title: 'Follow-up' },
];

function Refs({ refs }: { refs: number[] }) {
  return (
    <>
      {refs.map((r) => (
        <a key={r} href={`#src-${r}`} className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-semibold text-indigo-600 hover:bg-indigo-100" title={`Go to source ${r}`}>
          [{r}]
        </a>
      ))}
    </>
  );
}

function StatementItem({ s }: { s: Statement }) {
  return (
    <li className="space-y-1.5">
      <p className="text-sm leading-relaxed text-slate-700">{s.text}</p>
      <div className="flex flex-wrap items-center gap-2">
        <EvidenceBadge label={s.evidence_label} />
        {s.is_inference && (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">AI interpretation</span>
        )}
        <Refs refs={s.refs} />
      </div>
      {s.note && <p className="text-[11px] text-slate-400">{s.note}</p>}
    </li>
  );
}

function Block({ title, items }: { title: string; items: Statement[] }) {
  if (items.length === 0) return null;
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-4">
      <h4 className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-500">{title}</h4>
      <ul className="space-y-4">
        {items.map((s, i) => (
          <StatementItem key={`${title}-${i}`} s={s} />
        ))}
      </ul>
    </div>
  );
}

function NothingFound({ text }: { text: string }) {
  return <p className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-sm text-slate-500">{text}</p>;
}

function OpportunityCard({ o }: { o: Opportunity }) {
  return (
    <div className="space-y-2 rounded-xl border border-slate-100 bg-slate-50/60 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="text-sm font-bold text-slate-900">{o.title}</h4>
        <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold capitalize text-indigo-700">{o.type}</span>
      </div>
      {o.description && <p className="text-sm text-slate-700">{o.description}</p>}
      {o.why_relevant && (
        <p className="text-sm text-slate-600">
          <span className="font-semibold text-slate-700">Why it&apos;s relevant: </span>
          {o.why_relevant}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <EvidenceBadge label={o.evidence_label} />
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">AI interpretation</span>
        {o.refs.length > 0 ? <Refs refs={o.refs} /> : <span className="text-[11px] text-slate-400">No direct evidence cited</span>}
      </div>
    </div>
  );
}

function QuestionCard({ q }: { q: QuestionItem }) {
  return (
    <li className="space-y-1 rounded-xl border border-slate-100 bg-white p-4">
      <p className="text-sm font-semibold text-slate-900">{q.question}</p>
      {q.rationale && <p className="text-xs text-slate-500">Why ask: {q.rationale}</p>}
      {q.reveals && <p className="text-xs text-indigo-600">Could reveal: {q.reveals}</p>}
      {q.refs.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          <Refs refs={q.refs} />
        </div>
      )}
    </li>
  );
}

interface Props {
  data: BriefingResponse;
  actions?: React.ReactNode;
  backHref?: string;
}

export default function MeetingDashboard({ data, actions, backHref = '/history' }: Props) {
  const [tab, setTab] = useState<Tab>('overview');
  const { meeting, content: c, sources } = data;
  const ev = c.evidence_summary;

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <LayoutList className="h-3.5 w-3.5" /> },
    { id: 'company', label: 'Company Intel', icon: <Building2 className="h-3.5 w-3.5" /> },
    { id: 'person', label: 'People Intel', icon: <User className="h-3.5 w-3.5" /> },
    { id: 'opportunities', label: 'Opportunities', icon: <Lightbulb className="h-3.5 w-3.5" /> },
    { id: 'questions', label: 'Questions', icon: <HelpCircle className="h-3.5 w-3.5" /> },
  ];

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <Link href={backHref} className="flex w-fit items-center gap-1 text-sm font-medium text-slate-600 hover:text-slate-900">
        <ArrowLeft className="h-4 w-4" /> Back
      </Link>

      {data.is_mock && (
        <div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800" role="alert">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <span><strong>Demo data.</strong> This briefing was generated in mock mode with fictional sources. It is not real research.</span>
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Intelligence Brief: {meeting.organization_or_person}</h1>
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-500">
              {meeting.attendee_name && <span className="flex items-center gap-1.5"><User className="h-4 w-4" />{meeting.attendee_name}</span>}
              <span className="flex items-center gap-1.5"><Calendar className="h-4 w-4" />{formatDate(meeting.meeting_date)} · {formatTime(meeting.meeting_time)}</span>
            </div>
            <p className="mt-2 flex items-start gap-1.5 text-sm text-slate-600"><Target className="mt-0.5 h-4 w-4 shrink-0 text-indigo-500" />{meeting.purpose}</p>
            <p className="mt-2 text-xs text-slate-400">Generated {formatDateTime(data.generated_at)} from {ev.total_sources} web sources.</p>
          </div>
          {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <div className="flex w-full gap-1 overflow-x-auto rounded-xl bg-slate-200/60 p-1 sm:w-fit">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex shrink-0 items-center gap-1 rounded-lg px-4 py-2 text-xs font-bold ${tab === t.id ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-600'}`}
              >
                {t.icon} {t.label}
              </button>
            ))}
          </div>

          <div className="min-h-[300px] space-y-4 rounded-2xl border border-slate-200 bg-white p-6">
            {tab === 'overview' && (
              <>
                <Block title="Meeting overview" items={c.meeting_overview} />
                <Block title="Key insights" items={c.insights} />
                <Block title="Suggested discussion points" items={c.discussion_points} />
                <Block title="Recommended meeting strategy" items={c.strategy} />
                <Block title="Potential risks" items={c.risks} />
                {c.limitations.length > 0 && (
                  <div className="rounded-xl border border-amber-100 bg-amber-50/60 p-4">
                    <h4 className="mb-2 text-xs font-bold uppercase tracking-wide text-amber-700">Limitations & gaps</h4>
                    <ul className="list-disc space-y-1 pl-5 text-sm text-amber-900">
                      {c.limitations.map((l, i) => <li key={i}>{l}</li>)}
                    </ul>
                  </div>
                )}
              </>
            )}

            {tab === 'company' && (
              COMPANY_BLOCKS.every((b) => c.company[b.key].length === 0)
                ? <NothingFound text="No company information could be supported by the sources found." />
                : COMPANY_BLOCKS.map((b) => <Block key={b.key} title={b.title} items={c.company[b.key]} />)
            )}

            {tab === 'person' && (
              !c.attendee ? (
                <NothingFound text={meeting.attendee_name
                  ? `No reliable public professional information was found for ${meeting.attendee_name}, so this section was skipped rather than guessed.`
                  : 'No attendee was specified for this meeting.'} />
              ) : (
                <>
                  {c.attendee.identity_note && (
                    <p className="rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm text-amber-800">{c.attendee.identity_note}</p>
                  )}
                  {PERSON_BLOCKS.every((b) => c.attendee![b.key].length === 0)
                    ? <NothingFound text="The sources did not contain usable professional details about this person." />
                    : PERSON_BLOCKS.map((b) => <Block key={b.key} title={b.title} items={c.attendee![b.key]} />)}
                </>
              )
            )}

            {tab === 'opportunities' && (
              c.opportunities.length === 0
                ? <NothingFound text="No opportunities could be identified from the available evidence." />
                : c.opportunities.map((o, i) => <OpportunityCard key={i} o={o} />)
            )}

            {tab === 'questions' && (
              QUESTION_GROUPS.every((g) => c.questions[g.key].length === 0)
                ? <NothingFound text="No questions were generated." />
                : QUESTION_GROUPS.map((g) => c.questions[g.key].length > 0 && (
                    <div key={g.key}>
                      <h4 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">{g.title}</h4>
                      <ul className="space-y-2">{c.questions[g.key].map((q, i) => <QuestionCard key={i} q={q} />)}</ul>
                    </div>
                  ))
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="space-y-4 rounded-2xl border border-slate-200 bg-slate-100 p-4">
            <div className="flex items-center gap-2 border-b pb-2">
              <Newspaper className="h-4 w-4 text-slate-700" />
              <h3 className="text-xs font-bold text-slate-800">Latest 30-Day News Feed</h3>
            </div>
            {c.recent_developments.length === 0 && (
              <p className="rounded-xl bg-white p-3 text-xs text-slate-500">No recent news was found for this organisation.</p>
            )}
            {c.recent_developments.map((n) => (
              <div key={n.source_id} className="space-y-1 rounded-xl border bg-white p-3 shadow-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[10px] font-semibold text-slate-400">{formatDate(n.published_date)}</span>
                  <FreshnessBadge freshness={n.freshness} />
                </div>
                <h4 className="text-xs font-bold text-slate-900">{n.headline}</h4>
                <p className="text-[11px] text-slate-500">{n.summary}</p>
                <p className="text-[10px] text-slate-400">{n.summary_is_ai ? 'AI summary of the article' : 'Excerpt from the source'}</p>
                <div className="flex items-center gap-3 pt-1">
                  <a href={n.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 text-[11px] font-medium text-blue-600">
                    Source <ExternalLink className="h-3 w-3" />
                  </a>
                  <a href={`#src-${n.ref}`} className="text-[11px] font-semibold text-indigo-600">[{n.ref}]</a>
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="mb-3 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <h3 className="text-xs font-bold text-slate-800">Evidence summary</h3>
            </div>
            <dl className="space-y-1.5 text-xs">
              {([
                ['Verified', ev.verified, 'text-emerald-700'],
                ['Partially supported', ev.partially_supported, 'text-amber-700'],
                ['Needs verification', ev.needs_verification, 'text-rose-700'],
                ['Potentially outdated', ev.potentially_outdated, 'text-orange-700'],
              ] as const).map(([label, n, color]) => (
                <div key={label} className="flex justify-between"><dt className="text-slate-500">{label}</dt><dd className={`font-bold ${color}`}>{n}</dd></div>
              ))}
              <div className="mt-2 border-t pt-2 text-slate-500">
                {ev.total_sources} sources: {ev.recent_sources} recent, {ev.outdated_sources} outdated, {ev.undated_sources} undated
              </div>
            </dl>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <h3 className="text-lg font-bold text-slate-900">Sources</h3>
        <p className="mb-4 text-sm text-slate-400">Every statement above points to these retrieved pages. Dates are shown only when the source provided one.</p>
        <ol className="space-y-3">
          {sources.map((s) => (
            <li key={s.id} id={`src-${s.ref}`} className="scroll-mt-6 rounded-xl border border-slate-100 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-bold text-indigo-600">[{s.ref}]</span>
                <FreshnessBadge freshness={s.freshness} />
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] capitalize text-slate-500">{s.category}</span>
              </div>
              <a href={s.url} target="_blank" rel="noopener noreferrer" className="mt-1 block text-sm font-semibold text-slate-900 hover:text-indigo-700">{s.title}</a>
              <p className="break-all text-xs text-slate-400">{s.url}</p>
              <p className="mt-1 text-xs text-slate-500">Published: {formatDate(s.published_date)} · Retrieved: {formatDate(s.retrieved_at)}</p>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
