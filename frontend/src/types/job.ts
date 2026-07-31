export type JobType = 'onsite' | 'remote' | 'hybrid'
export type JobStatus = 'open' | 'closed'

export interface JobCreate {
  title: string
  description: string
  location?: string | null
  job_type?: JobType
}

export interface JobStatusUpdate {
  status: JobStatus
}

export interface CompanyOut {
  id: string
  name: string
}

export interface JobOut {
  id: string
  title: string
  description: string
  location: string | null
  job_type: JobType
  status: JobStatus
  company: CompanyOut
  created_at: string
}

export interface JobListParams {
  page?: number
  page_size?: number
  job_type?: JobType
  location?: string
}
