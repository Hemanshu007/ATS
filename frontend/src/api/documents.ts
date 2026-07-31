import { apiClient } from './client'
import type { DocumentOut, Paginated, PaginationParams } from '../types/common'

export const documentsApi = {
  mine: (params: PaginationParams = {}) =>
    apiClient.get<Paginated<DocumentOut>>('/documents/me', { params }).then((r) => r.data),

  remove: (documentId: string) =>
    apiClient.delete<{ message: string }>(`/documents/${documentId}`).then((r) => r.data),
}
