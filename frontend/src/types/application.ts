export type ApplicationStatus =
  | 'applied'
  | 'screening'
  | 'interview'
  | 'offer'
  | 'hired'
  | 'rejected'

export interface ApplicationOut {
  id: string
  job_id: string
  candidate_id: string
  document_id: string
  current_status: ApplicationStatus
  applied_at: string
}

export interface StatusUpdate {
  status: ApplicationStatus
  notes?: string | null
}

export interface StatusHistoryOut {
  status: ApplicationStatus
  changed_by: string
  changed_at: string
  notes: string | null
}

export interface ApplicationDetail {
  id: string
  job: {
    id: string
    title: string
    company: string
    job_type: string
  }
  candidate: {
    id: string
    name: string
  }
  current_status: ApplicationStatus
  applied_at: string
  interview_rounds: {
    round_number: number
    outcome: string
    scheduled_at: string | null
  }[]
  status_history: {
    status: ApplicationStatus
    changed_at: string
  }[]
}

export interface NoteCreate {
  content: string
}

export interface NoteOut {
  id: string
  content: string
  created_by: string
  created_at: string
}

export interface ResumeDownload {
  url?: string
  filename: string
  expires_in_seconds?: number
  expires_in_human?: string
}
