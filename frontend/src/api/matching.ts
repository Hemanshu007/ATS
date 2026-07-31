import { apiClient } from './client'
import type { JobMatches, SearchResult } from '../types/common'

export const matchingApi = {
  matches: (jobId: string, limit = 10) =>
    apiClient.get<JobMatches>(`/jobs/${jobId}/matches`, { params: { limit } }).then((r) => r.data),

  search: (jobId: string, query: string, limit = 5) =>
    apiClient
      .post<SearchResult>(`/jobs/${jobId}/search`, { query }, { params: { limit } })
      .then((r) => r.data),
}
