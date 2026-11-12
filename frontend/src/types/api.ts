// API contract with the FastAPI backend. Keep in sync with backend/app/schemas/*.

export type MeetingStatus = 'created' | 'researching' | 'ready' | 'failed';
export type EvidenceLabel =
  | 'verified'
  | 'partially_supported'
  | 'needs_verification'
  | 'potentially_outdated';
export type Freshness = 'recent' | 'potentially_outdated' | 'unknown';
export type SourceCategory = 'news' | 'company' | 'person' | 'other';

export interface MeetingFormValues {
  organization_or_person: string;
  attendee_name: string | null;
  meeting_date: string; // YYYY-MM-DD
  meeting_time: string; // HH:MM
  purpose: string;
}

export interface Meeting {
  id: number;
  organization_or_person: string;
  attendee_name: string | null;
  meeting_date: string;
  meeting_time: string; // HH:MM:SS
  purpose: string;
  status: MeetingStatus;
  progress_stage: string | null;
  progress_percent: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface HistoryItem extends Meeting {
  source_count: number;
  has_briefing: boolean;
  generated_at: string | null;
}

export interface HistoryList {
  items: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface DashboardStats {
  total_meetings: number;
  briefings_ready: number;
  upcoming_meetings: number;
  researching: number;
  failed: number;
}

export interface ResearchStatus {
  meeting_id: number;
  status: MeetingStatus;
  stage: string | null;
  progress_percent: number;
  error_message: string | null;
  mock_mode: boolean;
}

export interface Statement {
  text: string;
  source_ids: number[];
  refs: number[];
  evidence_label: EvidenceLabel;
  is_inference: boolean;
  note: string | null;
  claim_id: number | null;
}

export interface Opportunity {
  title: string;
  type: string;
  description: string;
  why_relevant: string;
  source_ids: number[];
  refs: number[];
  evidence_label: EvidenceLabel;
  is_inference: boolean;
  note: string | null;
}

export interface QuestionItem {
  question: string;
  rationale: string | null;
  reveals: string | null;
  source_ids: number[];
  refs: number[];
}

export interface NewsItem {
  source_id: number;
  ref: number;
  headline: string;
  summary: string;
  summary_is_ai: boolean;
  published_date: string | null;
  url: string;
  freshness: Freshness;
}

export interface CompanySection {
  overview: Statement[];
  business_model: Statement[];
  products_services: Statement[];
  competitors: Statement[];
  strategic_initiatives: Statement[];
  challenges: Statement[];
}

export interface AttendeeSection {
  role: Statement[];
  experience: Statement[];
  achievements: Statement[];
  expertise: Statement[];
  public_content: Statement[];
  identity_note: string | null;
}

export interface EvidenceSummary {
  total_sources: number;
  recent_sources: number;
  outdated_sources: number;
  undated_sources: number;
  total_claims: number;
  verified: number;
  partially_supported: number;
  needs_verification: number;
  potentially_outdated: number;
}

export interface Questions {
  strategic: QuestionItem[];
  technical: QuestionItem[];
  business: QuestionItem[];
  collaboration: QuestionItem[];
  follow_up: QuestionItem[];
}

export interface BriefingContent {
  meeting_overview: Statement[];
  company: CompanySection;
  attendee: AttendeeSection | null;
  recent_developments: NewsItem[];
  insights: Statement[];
  opportunities: Opportunity[];
  risks: Statement[];
  discussion_points: Statement[];
  strategy: Statement[];
  questions: Questions;
  evidence_summary: EvidenceSummary;
  limitations: string[];
}

export interface Source {
  id: number;
  ref: number;
  category: SourceCategory;
  url: string;
  title: string;
  published_date: string | null;
  retrieved_at: string;
  snippet: string | null;
  freshness: Freshness;
}

export interface BriefingResponse {
  meeting: Meeting;
  is_mock: boolean;
  generated_at: string;
  content: BriefingContent;
  sources: Source[];
}

export interface HealthInfo {
  status: string;
  application: string;
  database: string;
  mock_mode: boolean;
  tavily_configured: boolean;
  anthropic_configured: boolean;
  llm_provider: string;
  llm_model: string;
  llm_configured: boolean;
}
