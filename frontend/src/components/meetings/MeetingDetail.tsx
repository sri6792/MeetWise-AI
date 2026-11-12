'use client';
import { use, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Download, Pencil, PlayCircle, RefreshCw, Trash2, Loader2, Calendar, User, Target } from 'lucide-react';
import PageShell from '@/components/layout/PageShell';
import IntelligenceLoader from '@/components/research/IntelligenceLoader';
import MeetingDashboard from '@/components/research/MeetingDashboard';
import EditMeetingDialog from '@/components/meetings/EditMeetingDialog';
import { StatusPill } from '@/components/ui/Badges';
import { EmptyState, ErrorBanner, Spinner } from '@/components/ui/States';
import { useAsync } from '@/hooks/useAsync';
import { useResearchPolling } from '@/hooks/useResearchPolling';
import { api, errorMessage, saveBlob } from '@/lib/api';
import { formatDate, formatTime } from '@/lib/format';
import type { Meeting, MeetingFormValues, ResearchStatus } from '@/types/api';

type Busy = 'pdf' | 'rerun' | 'delete' | 'edit' | null;

const btn = 'inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60';

export default function MeetingDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const meetingId = Number(id);
  const valid = Number.isInteger(meetingId) && meetingId > 0;
  const router = useRouter();

  const meetingQ = useAsync(valid ? () => api.getMeeting(meetingId) : null, `meeting-${id}`);
  const meeting = meetingQ.data;
  const researching = meeting?.status === 'researching';
  const { status: liveStatus, error: pollError } = useResearchPolling(valid ? meetingId : null, researching, () => meetingQ.reload());

  const ready = meeting?.status === 'ready';
  const briefingQ = useAsync(ready ? () => api.getBriefing(meetingId) : null, `briefing-${id}-${meeting?.updated_at ?? ''}`);

  const [busy, setBusy] = useState<Busy>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  const run = async (kind: Exclude<Busy, null>, fn: () => Promise<void>) => {
    setBusy(kind);
    setActionError(null);
    try {
      await fn();
    } catch (e) {
      setActionError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  const startResearch = () => run('rerun', async () => {
    await api.startResearch(meetingId);
    meetingQ.reload();
  });
  const rerun = () => {
    if (window.confirm('Re-run research? The current briefing will be replaced.')) void startResearch();
  };
  const downloadPdf = () => run('pdf', async () => {
    const { blob, filename } = await api.downloadPdf(meetingId);
    saveBlob(blob, filename);
  });
  const remove = () => {
    if (!window.confirm('Delete this meeting and its briefing? This cannot be undone.')) return;
    void run('delete', async () => {
      await api.deleteMeeting(meetingId);
      router.push('/history');
    });
  };
  const saveEdit = (v: MeetingFormValues) => run('edit', async () => {
    await api.updateMeeting(meetingId, v);
    setEditing(false);
    meetingQ.reload();
  });

  const editBtn = (
    <button onClick={() => setEditing(true)} className={`${btn} border border-slate-200 bg-white text-slate-700 hover:bg-slate-50`}>
      <Pencil size={16} /> Edit
    </button>
  );
  const deleteBtn = (
    <button onClick={remove} disabled={busy === 'delete'} className={`${btn} border border-rose-200 bg-white text-rose-600 hover:bg-rose-50`}>
      <Trash2 size={16} /> Delete
    </button>
  );

  const summary = (m: Meeting) => (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-slate-900">{m.organization_or_person}</h1>
        <StatusPill status={m.status} />
      </div>
      <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-slate-500">
        {m.attendee_name && <span className="flex items-center gap-1.5"><User className="h-4 w-4" />{m.attendee_name}</span>}
        <span className="flex items-center gap-1.5"><Calendar className="h-4 w-4" />{formatDate(m.meeting_date)} · {formatTime(m.meeting_time)}</span>
      </div>
      <p className="mt-2 flex items-start gap-1.5 text-sm text-slate-600"><Target className="mt-0.5 h-4 w-4 shrink-0 text-indigo-500" />{m.purpose}</p>
    </div>
  );

  let body: React.ReactNode;
  if (!valid) {
    body = <EmptyState title="Meeting not found" description="This link doesn’t point to a valid meeting." action={<Link href="/history" className="font-semibold text-indigo-600">Go to history</Link>} />;
  } else if (meetingQ.error && !meeting) {
    body = <ErrorBanner message={meetingQ.error} onRetry={meetingQ.reload}><Link href="/history" className="rounded-lg border border-rose-300 px-3 py-1.5 text-sm font-semibold text-rose-700">History</Link></ErrorBanner>;
  } else if (!meeting) {
    body = <Spinner label="Loading meeting…" />;
  } else if (meeting.status === 'researching') {
    const status: ResearchStatus = liveStatus ?? {
      meeting_id: meeting.id, status: 'researching', stage: meeting.progress_stage,
      progress_percent: meeting.progress_percent ?? 0, error_message: null, mock_mode: false,
    };
    body = (
      <div className="space-y-6">
        {summary(meeting)}
        <IntelligenceLoader status={status} error={pollError} />
      </div>
    );
  } else if (meeting.status === 'ready') {
    if (briefingQ.error) body = <ErrorBanner message={briefingQ.error} onRetry={briefingQ.reload} />;
    else if (!briefingQ.data) body = <Spinner label="Loading briefing…" />;
    else {
      body = (
        <MeetingDashboard
          data={briefingQ.data}
          actions={
            <>
              <button onClick={downloadPdf} disabled={busy === 'pdf'} className={`${btn} bg-indigo-600 text-white hover:bg-indigo-700`}>
                {busy === 'pdf' ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />} Download PDF
              </button>
              <button onClick={rerun} disabled={busy === 'rerun'} className={`${btn} border border-slate-200 bg-white text-slate-700 hover:bg-slate-50`}>
                <RefreshCw size={16} /> Re-run research
              </button>
              {editBtn}
              {deleteBtn}
            </>
          }
        />
      );
    }
  } else {
    // created or failed
    const failed = meeting.status === 'failed';
    body = (
      <div className="space-y-6">
        {summary(meeting)}
        {failed && <ErrorBanner message={meeting.error_message ?? 'Research failed. Please try again.'} />}
        {!failed && (
          <EmptyState
            title="Research hasn’t started yet"
            description="Start research to gather recent news, company and attendee information, and generate your briefing."
          />
        )}
        <div className="flex flex-wrap gap-2">
          <button onClick={startResearch} disabled={busy === 'rerun'} className={`${btn} bg-indigo-600 text-white hover:bg-indigo-700`}>
            {busy === 'rerun' ? <Loader2 size={16} className="animate-spin" /> : <PlayCircle size={16} />}
            {failed ? 'Retry research' : 'Start research'}
          </button>
          {editBtn}
          {deleteBtn}
        </div>
      </div>
    );
  }

  return (
    <PageShell>
      <div className="mx-auto max-w-6xl space-y-4">
        {actionError && <ErrorBanner message={actionError} />}
        {body}
      </div>
      {editing && meeting && (
        <EditMeetingDialog meeting={meeting} onSave={saveEdit} onClose={() => setEditing(false)} saving={busy === 'edit'} error={actionError} />
      )}
    </PageShell>
  );
}
