
'use client';

import { CheckCircle2, XCircle } from 'lucide-react';
import PageShell from '@/components/layout/PageShell';
import { ErrorBanner, Spinner } from '@/components/ui/States';
import { useAsync } from '@/hooks/useAsync';
import { api } from '@/lib/api';

function Row({ label, ok, detail }: { label: string; ok: boolean; detail?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 py-3 last:border-0">
      <span className="text-sm text-slate-700">{label}</span>
      <span className={`flex items-center gap-1.5 text-sm font-semibold ${ok ? 'text-emerald-600' : 'text-rose-600'}`}>
        {ok ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
        {detail ?? (ok ? 'Configured' : 'Not configured')}
      </span>
    </div>
  );
}

export default function SettingsView() {
  const health = useAsync(() => api.health(), 'health');
  const h = health.data;

  return (
    <PageShell>
      <div className="mx-auto max-w-2xl space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Settings &amp; System Status</h1>
          <p className="mt-1 text-slate-500">Check that the backend and your API keys are ready.</p>
        </div>

        {health.error && <ErrorBanner message={health.error} onRetry={health.reload} />}
        {!h && !health.error && <Spinner />}

        {h && (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <Row label="Backend" ok={h.status === 'healthy'} detail={h.status === 'healthy' ? 'Healthy' : 'Degraded'} />
            <Row label="Database" ok={h.database === 'ok'} detail={h.database === 'ok' ? 'Connected' : 'Unavailable'} />
            <Row label="Tavily API key (web research)" ok={h.tavily_configured} />
            <Row
              label={`AI model (${h.llm_provider === 'anthropic' ? 'Claude' : 'OpenAI-compatible'})`}
              ok={h.llm_configured}
              detail={h.llm_configured ? (h.llm_model || 'Configured') : 'Not configured'}
            />
            <div className="flex items-center justify-between py-3">
              <span className="text-sm text-slate-700">Data mode</span>
              <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${h.mock_mode ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'}`}>
                {h.mock_mode ? 'Demo data (MOCK_MODE)' : 'Real research'}
              </span>
            </div>
          </div>
        )}
      </div>
    </PageShell>
  );
}
