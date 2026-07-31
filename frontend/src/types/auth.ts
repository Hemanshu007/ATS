export type UserRole = 'candidate' | 'recruiter'

export interface RegisterRequest {
  email: string
  password: string
  role: UserRole
  name: string
  company_name?: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  role: UserRole
}

export interface UserOut {
  id: string
  email: string
  role: UserRole
  created_at: string
}

export interface CandidateProfileOut {
  id: string
  name: string
  phone: string | null
  location: string | null
}

export interface RecruiterProfileOut {
  id: string
  name: string
  phone: string | null
  company_id: string
}

export interface MeResponse {
  user: UserOut
  profile: CandidateProfileOut | RecruiterProfileOut
}
