import { apiClient } from './client'
import type { Paginated, PaginationParams, RecruiterDashboard, RecruiterJobSummary } from '../types/common'

export const recruitersApi = {
  dashboard: () => apiClient.get<RecruiterDashboard>('/recruiters/me/dashboard').then((r) => r.data),

  myJobs: (params: PaginationParams = {}) =>
    apiClient
      .get<Paginated<RecruiterJobSummary>>('/recruiters/me/jobs', { params })
      .then((r) => r.data),
}
