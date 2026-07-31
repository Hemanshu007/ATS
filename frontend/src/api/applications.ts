import { apiClient } from './client'
import type {
  ApplicationDetail,
  ApplicationOut,
  ApplicationStatus,
  NoteCreate,
  NoteOut,
  StatusHistoryOut,
  StatusUpdate,
} from '../types/application'
import type { Paginated, PaginationParams } from '../types/common'

export const applicationsApi = {
  apply: (jobId: string, resume: File) => {
    const form = new FormData()
    form.append('job_id', jobId)
    form.append('resume', resume)
    return apiClient
      .post<ApplicationOut>('/applications/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  myApplications: (params: PaginationParams = {}) =>
    apiClient.get<Paginated<ApplicationOut>>('/applications/me', { params }).then((r) => r.data),

  forJob: (jobId: string, params: PaginationParams & { status?: ApplicationStatus } = {}) =>
    apiClient
      .get<Paginated<ApplicationOut>>(`/applications/job/${jobId}`, { params })
      .then((r) => r.data),

  detail: (appId: string) =>
    apiClient.get<ApplicationDetail>(`/applications/${appId}`).then((r) => r.data),

  updateStatus: (appId: string, body: StatusUpdate) =>
    apiClient.patch<ApplicationOut>(`/applications/${appId}/status`, body).then((r) => r.data),

  history: (appId: string) =>
    apiClient.get<StatusHistoryOut[]>(`/applications/${appId}/history`).then((r) => r.data),

  // The backend returns either a raw PDF stream (local storage) or a JSON
  // envelope with a presigned S3 URL, depending on server config — this needs
  // an auth header either way, so it can't just be a plain <a href>.
  downloadResume: async (appId: string) => {
    const response = await apiClient.get(`/applications/${appId}/resume`, {
      responseType: 'blob',
    })
    const contentType = response.headers['content-type'] as string

    if (contentType?.includes('application/json')) {
      const text = await (response.data as Blob).text()
      const parsed = JSON.parse(text) as { url?: string; filename: string; message?: string }
      if (parsed.url) {
        window.open(parsed.url, '_blank')
      }
      return parsed
    }

    const blobUrl = URL.createObjectURL(response.data as Blob)
    const disposition = response.headers['content-disposition'] as string | undefined
    const filenameMatch = disposition?.match(/filename="?([^"]+)"?/)
    const filename = filenameMatch?.[1] ?? 'resume.pdf'

    const link = document.createElement('a')
    link.href = blobUrl
    link.download = filename
    link.click()
    URL.revokeObjectURL(blobUrl)
    return { filename }
  },

  createNote: (appId: string, body: NoteCreate) =>
    apiClient.post<NoteOut>(`/applications/${appId}/notes`, body).then((r) => r.data),

  listNotes: (appId: string) =>
    apiClient.get<NoteOut[]>(`/applications/${appId}/notes`).then((r) => r.data),
}
