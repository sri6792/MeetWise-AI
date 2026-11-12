import { Suspense } from 'react';
import MeetingDetail from '@/components/meetings/MeetingDetail';

// With Cache Components, reading route params must sit behind a <Suspense> boundary.
export default function MeetingPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<div className="p-10 text-center text-sm text-slate-500">Loading…</div>}>
      <MeetingDetail params={params} />
    </Suspense>
  );
}
