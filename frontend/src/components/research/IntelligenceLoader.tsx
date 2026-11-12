'use client';
import React from 'react';
import { Loader2, CheckCircle2, Circle, Sparkles } from 'lucide-react';
import type { ResearchStatus } from '@/types/api';

// Order matches the backend pipeline stages (research_service.py)
const STEPS: { key: string; label: string }[] = [
  { key: 'searching_news', label: 'Searching the last 30 days of news…' },
  { key: 'researching_company', label: 'Researching the company, products and competitors…' },
  { key: 'researching_people', label: 'Looking up the attendee’s public professional background…' },
  { key: 'verifying_evidence', label: 'Recording sources and checking freshness…' },
  { key: 'analysing_company', label: 'Analysing company evidence with AI…' },
  { key: 'analysing_person', label: 'Analysing the attendee profile…' },
  { key: 'generating_briefing', label: 'Generating insights, opportunities and questions…' },
];

interface Props {
  status: ResearchStatus | null;
  error?: string | null;
}

/** Shows REAL progress reported by the backend (no timers). */
export default function IntelligenceLoader({ status, error }: Props) {
  const stage = status?.stage ?? 'queued';
  const currentStep = STEPS.findIndex((s) => s.key === stage);
  const percent = Math.min(100, Math.max(0, status?.progress_percent ?? 0));

  return (
    <div className="max-w-md mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl p-6 text-center space-y-6">
      <div className="relative mx-auto w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center animate-pulse">
        <Sparkles className="h-8 w-8 text-blue-600" />
      </div>
      <div>
        <h3 className="text-lg font-bold text-slate-900">Researching Target Ecosystem</h3>
        <p className="text-xs text-slate-400">
          Real research takes about 30 to 90 seconds. You can leave this page; progress is saved.
        </p>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full bg-indigo-600 transition-all duration-700" style={{ width: `${percent}%` }} />
      </div>

      <div className="text-left space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-100">
        {STEPS.map((step, idx) => (
          <div key={step.key} className={`flex items-center gap-3 text-xs ${idx <= currentStep ? 'opacity-100' : 'opacity-30'}`}>
            {idx < currentStep ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            ) : idx === currentStep ? (
              <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
            ) : (
              <Circle className="h-4 w-4 text-slate-300" />
            )}
            <span className={idx === currentStep ? 'text-blue-700 font-semibold' : 'text-slate-600'}>{step.label}</span>
          </div>
        ))}
      </div>

      {status?.mock_mode && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700">
          Demo mode: this run uses sample data, not real research.
        </p>
      )}
      {error && <p className="text-xs text-amber-600">Connection problem, retrying: {error}</p>}
    </div>
  );
}
