import { apiClient } from './client'
import type { InterviewCreate, InterviewOut, OutcomeUpdate } from '../types/interview'

export const interviewsApi = {
  create: (body: InterviewCreate) =>
    apiClient.post<InterviewOut>('/interviews/', body).then((r) => r.data),

  forApplication: (appId: string) =>
    apiClient.get<InterviewOut[]>(`/interviews/application/${appId}`).then((r) => r.data),

  detail: (interviewId: string) =>
    apiClient.get<InterviewOut>(`/interviews/${interviewId}`).then((r) => r.data),

  updateOutcome: (interviewId: string, body: OutcomeUpdate) =>
    apiClient.patch<InterviewOut>(`/interviews/${interviewId}/outcome`, body).then((r) => r.data),

  cancel: (interviewId: string) =>
    apiClient
      .delete<{ message: string; id: string }>(`/interviews/${interviewId}`)
      .then((r) => r.data),
}
