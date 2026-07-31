export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export interface PaginationParams {
  page?: number
  page_size?: number
}

export interface CompanyDetail {
  id: string
  name: string
  industry: string | null
  location: string | null
  created_at: string
  open_jobs_count: number
}

export interface CompanyUpdate {
  name?: string
  industry?: string
  location?: string
}

export interface RecruiterDashboard {
  total_jobs: number
  open_jobs: number
  closed_jobs: number
  total_applications: number
  pipeline_summary: Record<string, number>
}

export interface RecruiterJobSummary {
  id: string
  title: string
  status: string
  job_type: string
  application_count: number
  created_at: string
}

export interface CandidateProfile {
  id: string
  name: string
  phone: string | null
  location: string | null
  email: string
  created_at: string
}

export interface CandidateProfileUpdate {
  name?: string
  phone?: string
  location?: string
}

export interface CandidateDashboard {
  total_applications: number
  status_breakdown: Record<string, number>
  recent_applications: {
    job_title: string
    company_name: string
    current_status: string
    applied_at: string
  }[]
}

export interface DocumentOut {
  id: string
  original_filename: string
  uploaded_at: string
}

export interface CandidateMatch {
  document_id: string
  candidate_id: string
  similarity_score: number
  parsed_data: Record<string, unknown>
}

export interface JobMatches {
  job_id: string
  matches: CandidateMatch[]
}

export interface SearchMatch {
  document_id: string
  candidate_id: string
  relevance_summary: string
  supporting_evidence: string[]
}

export interface SearchResult {
  query: string
  matches: SearchMatch[]
}
