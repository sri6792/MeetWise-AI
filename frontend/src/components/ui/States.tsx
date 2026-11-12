import type { ReactNode } from 'react';
import { AlertTriangle, Inbox, Loader2 } from 'lucide-react';

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-500" role="status">
      <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function EmptyState({
  title, description, action,
}: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-14 text-center">
      <div className="mb-4 rounded-full bg-indigo-50 p-4 text-indigo-600">
        <Inbox size={26} />
      </div>
      <h3 className="text-lg font-bold text-slate-900">{title}</h3>
      {description && <p className="mt-1 max-w-md text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorBanner({
  message, onRetry, children,
}: { message: string; onRetry?: () => void; children?: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-5 sm:flex-row sm:items-center sm:justify-between" role="alert">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" />
        <p className="text-sm text-rose-800">{message}</p>
      </div>
      <div className="flex shrink-0 gap-2">
        {children}
        {onRetry && (
          <button onClick={onRetry} className="rounded-lg bg-rose-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-rose-700">
            Try again
          </button>
        )}
      </div>
    </div>
  );
}
