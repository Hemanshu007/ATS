export type InterviewOutcome = 'pending' | 'pass' | 'fail' | 'cancelled'

export interface InterviewCreate {
  application_id: string
  round_number: number
  scheduled_at?: string | null
  conducted_by?: string | null
}

export interface OutcomeUpdate {
  outcome: 'pending' | 'pass' | 'fail'
  notes?: string | null
}

export interface InterviewOut {
  id: string
  application_id: string
  round_number: number
  scheduled_at: string | null
  conducted_by: string | null
  outcome: InterviewOutcome
  notes: string | null
  created_at: string
}
