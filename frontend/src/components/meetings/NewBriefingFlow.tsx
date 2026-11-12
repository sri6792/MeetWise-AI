'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import PageShell from '@/components/layout/PageShell';
import SmartMeetingCreation from '@/components/meetings/SmartMeetingCreation';
import { ErrorBanner } from '@/components/ui/States';
import { api, errorMessage } from '@/lib/api';
import type { MeetingFormValues } from '@/types/api';

/** Create meeting -> start research -> open the meeting page, which shows live progress. */
export default function NewBriefingFlow() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<number | null>(null);

  const submit = async (values: MeetingFormValues) => {
    setSubmitting(true);
    setError(null);
    let id: number | null = null;
    try {
      const meeting = await api.createMeeting(values);
      id = meeting.id;
      setSavedId(id);
      await api.startResearch(id);
      router.push(`/meetings/${id}`);
    } catch (e) {
      // If the meeting was saved but research could not start (e.g. missing API keys), say so.
      setError(errorMessage(e));
      setSubmitting(false);
    }
  };

  return (
    <PageShell>
      <div className="mx-auto max-w-xl space-y-4">
        <SmartMeetingCreation onSubmit={submit} submitting={submitting} />
        {error && savedId !== null && (
          <ErrorBanner message={`Your meeting was saved, but research could not start: ${error}`}>
            <Link href={`/meetings/${savedId}`} className="rounded-lg border border-rose-300 px-3 py-1.5 text-sm font-semibold text-rose-700">
              Open meeting
            </Link>
          </ErrorBanner>
        )}
        {error && savedId === null && <ErrorBanner message={error} />}
      </div>
    </PageShell>
  );
}
