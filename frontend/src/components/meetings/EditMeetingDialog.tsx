'use client';
import { X } from 'lucide-react';
import type { Meeting, MeetingFormValues } from '@/types/api';
import SmartMeetingCreation from '@/components/meetings/SmartMeetingCreation';

interface Props {
  meeting: Meeting;
  onSave: (v: MeetingFormValues) => void | Promise<void>;
  onClose: () => void;
  saving: boolean;
  error: string | null;
}

export default function EditMeetingDialog({ meeting, onSave, onClose, saving, error }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4" role="dialog" aria-modal="true">
      <div className="relative my-8 w-full max-w-xl">
        <button onClick={onClose} aria-label="Close" className="absolute right-3 top-3 z-10 rounded-full bg-white/20 p-1.5 text-white hover:bg-white/30">
          <X size={18} />
        </button>
        <SmartMeetingCreation
          heading="Edit meeting"
          description="Changing the details does not refresh the research. Re-run research afterwards to update the briefing."
          submitLabel="Save changes"
          initial={meeting}
          onSubmit={onSave}
          submitting={saving}
          error={error}
        />
      </div>
    </div>
  );
}
