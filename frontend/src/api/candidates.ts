import { apiClient } from './client'
import type { CandidateDashboard, CandidateProfile, CandidateProfileUpdate } from '../types/common'

export const candidatesApi = {
  profile: () => apiClient.get<CandidateProfile>('/candidates/me/profile').then((r) => r.data),

  updateProfile: (body: CandidateProfileUpdate) =>
    apiClient.patch<CandidateProfile>('/candidates/me/profile', body).then((r) => r.data),

  dashboard: () =>
    apiClient.get<CandidateDashboard>('/candidates/me/dashboard').then((r) => r.data),
}
