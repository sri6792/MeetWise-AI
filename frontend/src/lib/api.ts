import type {
  BriefingResponse, DashboardStats, HealthInfo, HistoryList, Meeting, MeetingFormValues,
  MeetingStatus, ResearchStatus, Source, SourceCategory,
} from '@/types/api';

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : 'Something went wrong. Please try again.';
}

/** FastAPI returns `detail` as a string, or as a list of {loc, msg} for validation errors. */
function readDetail(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) {
      return d
        .map((x: { loc?: unknown[]; msg?: string }) => {
          const field = Array.isArray(x.loc) ? String(x.loc[x.loc.length - 1]).replace(/_/g, ' ') : '';
          return field ? `${field}: ${x.msg ?? 'invalid'}` : (x.msg ?? 'invalid');
        })
        .join('; ');
    }
  }
  return fallback;
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(`Cannot reach the MeetWise backend at ${API_URL}. Is it running?`, 0);
  }
  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(readDetail(body, `Request failed (HTTP ${res.status})`), res.status);
  }
  return res;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await send(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function qs(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : '';
}

export interface HistoryQuery {
  q?: string;
  status?: MeetingStatus | '';
  sort?: 'date_desc' | 'date_asc' | 'created_desc';
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export const api = {
  health: () => request<HealthInfo>('/health'),

  createMeeting: (v: MeetingFormValues) =>
    request<Meeting>('/api/meetings', { method: 'POST', body: JSON.stringify(v) }),
  getMeeting: (id: number) => request<Meeting>(`/api/meetings/${id}`),
  updateMeeting: (id: number, v: Partial<MeetingFormValues>) =>
    request<Meeting>(`/api/meetings/${id}`, { method: 'PATCH', body: JSON.stringify(v) }),
  deleteMeeting: (id: number) => request<void>(`/api/meetings/${id}`, { method: 'DELETE' }),

  startResearch: (id: number) =>
    request<ResearchStatus>(`/api/meetings/${id}/research`, { method: 'POST' }),
  getStatus: (id: number) => request<ResearchStatus>(`/api/meetings/${id}/status`),
  getBriefing: (id: number) => request<BriefingResponse>(`/api/meetings/${id}/briefing`),
  getSources: (id: number, category?: SourceCategory) =>
    request<Source[]>(`/api/meetings/${id}/sources${qs({ category })}`),

  listHistory: (q: HistoryQuery = {}) => request<HistoryList>(`/api/history${qs({ ...q })}`),
  getStats: (today?: string) => request<DashboardStats>(`/api/history/stats${qs({ today })}`),

  /** Downloads the PDF and returns it with the server-suggested filename. */
  async downloadPdf(id: number): Promise<{ blob: Blob; filename: string }> {
    const res = await send(`/api/meetings/${id}/pdf`);
    const disposition = res.headers.get('Content-Disposition') ?? '';
    const match = /filename="?([^";]+)"?/i.exec(disposition);
    return { blob: await res.blob(), filename: match?.[1] ?? `MeetWise-Briefing-${id}.pdf` };
  },
};

export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
