'use client';
import React, { useState } from 'react';
import { Calendar, Clock, Building2, User, Target, Sparkles, Loader2 } from 'lucide-react';
import type { MeetingFormValues } from '@/types/api';

const PRESETS: { label: string; text: string }[] = [
  { label: 'Sales Pitch', text: 'Sales pitch to introduce our product and understand their needs' },
  { label: 'Partnership', text: 'Explore a partnership and identify areas of collaboration' },
  { label: 'Discovery', text: 'Discovery call to learn about their priorities and challenges' },
];

interface Props {
  onSubmit: (values: MeetingFormValues) => void | Promise<void>;
  submitting?: boolean;
  error?: string | null;
  initial?: Partial<MeetingFormValues>;
  heading?: string;
  description?: string;
  submitLabel?: string;
}

const inputClass =
  'w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 text-slate-950';

export default function SmartMeetingCreation({
  onSubmit,
  submitting = false,
  error = null,
  initial,
  heading = 'Smart Meeting Intelligence',
  description = 'Enter details to look up recent news and professional backgrounds.',
  submitLabel = 'Generate Intelligence Brief',
}: Props) {
  const [targetName, setTargetName] = useState(initial?.organization_or_person ?? '');
  const [attendee, setAttendee] = useState(initial?.attendee_name ?? '');
  const [date, setDate] = useState(initial?.meeting_date ?? '');
  const [time, setTime] = useState((initial?.meeting_time ?? '').slice(0, 5));
  const [purpose, setPurpose] = useState(initial?.purpose ?? '');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const org = targetName.trim();
    const why = purpose.trim();
    if (org.length < 2) return setLocalError('Enter the company or person you are meeting (at least 2 characters).');
    if (!date || !time) return setLocalError('Choose the meeting date and time.');
    if (why.length < 5) return setLocalError('Describe the purpose of the meeting (at least 5 characters).');
    setLocalError(null);
    void onSubmit({
      organization_or_person: org,
      attendee_name: attendee.trim() || null,
      meeting_date: date,
      meeting_time: time,
      purpose: why,
    });
  };

  const shownError = localError ?? error;

  return (
    <div className="max-w-xl mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden">
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-8 text-white">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-amber-300 fill-amber-300" />
          {heading}
        </h2>
        <p className="text-blue-100 text-sm mt-1">{description}</p>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-5" noValidate>
        <div className="space-y-2">
          <label htmlFor="org" className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <Building2 className="h-4 w-4 text-slate-400" /> Company or Person&apos;s Name
          </label>
          <input
            id="org"
            type="text"
            maxLength={200}
            placeholder="e.g. Stripe or Jane Doe"
            className={inputClass}
            value={targetName}
            onChange={(e) => setTargetName(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="attendee" className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <User className="h-4 w-4 text-slate-400" /> Attendee name <span className="font-normal text-slate-400">(optional)</span>
          </label>
          <input
            id="attendee"
            type="text"
            maxLength={200}
            placeholder="Who will you be meeting? e.g. Jane Doe"
            className={inputClass}
            value={attendee}
            onChange={(e) => setAttendee(e.target.value)}
          />
          <p className="text-xs text-slate-400">Only public professional information is researched.</p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label htmlFor="date" className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <Calendar className="h-4 w-4 text-slate-400" /> Date
            </label>
            <input id="date" type="date" className={inputClass} value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div className="space-y-2">
            <label htmlFor="time" className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <Clock className="h-4 w-4 text-slate-400" /> Time
            </label>
            <input id="time" type="time" className={inputClass} value={time} onChange={(e) => setTime(e.target.value)} />
          </div>
        </div>

        <div className="space-y-2">
          <label htmlFor="purpose" className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <Target className="h-4 w-4 text-slate-400" /> Goal of the meeting
          </label>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => setPurpose(p.text)}
                className={`px-4 py-2 text-xs font-medium rounded-full border transition-all ${
                  purpose === p.text ? 'bg-blue-50 border-blue-500 text-blue-700' : 'bg-white text-slate-600'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <textarea
            id="purpose"
            rows={3}
            maxLength={2000}
            placeholder="Describe what you want from this meeting. The more specific, the better the briefing."
            className={inputClass}
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
          />
        </div>

        {shownError && (
          <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {shownError}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="flex w-full items-center justify-center gap-2 py-3 bg-slate-950 text-white font-medium rounded-xl hover:bg-slate-800 transition-all disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
          {submitting ? 'Saving…' : submitLabel}
        </button>
      </form>
    </div>
  );
}
