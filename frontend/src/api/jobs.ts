import { apiClient } from './client'
import type { JobCreate, JobListParams, JobOut, JobStatusUpdate } from '../types/job'
import type { Paginated } from '../types/common'

export const jobsApi = {
  list: (params: JobListParams = {}) =>
    apiClient.get<Paginated<JobOut>>('/jobs/', { params }).then((r) => r.data),

  get: (jobId: string) => apiClient.get<JobOut>(`/jobs/${jobId}`).then((r) => r.data),

  create: (body: JobCreate) => apiClient.post<JobOut>('/jobs/', body).then((r) => r.data),

  updateStatus: (jobId: string, body: JobStatusUpdate) =>
    apiClient.patch<JobOut>(`/jobs/${jobId}/status`, body).then((r) => r.data),

  remove: (jobId: string) =>
    apiClient.delete<{ message: string }>(`/jobs/${jobId}`).then((r) => r.data),
}
