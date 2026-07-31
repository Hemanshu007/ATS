import { apiClient } from './client'
import type { CompanyDetail, CompanyUpdate, Paginated, PaginationParams } from '../types/common'
import type { CompanyOut, JobOut } from '../types/job'

export const companiesApi = {
  list: (params: PaginationParams = {}) =>
    apiClient.get<Paginated<CompanyOut>>('/companies/', { params }).then((r) => r.data),

  get: (companyId: string) =>
    apiClient.get<CompanyDetail>(`/companies/${companyId}`).then((r) => r.data),

  jobs: (companyId: string, params: PaginationParams = {}) =>
    apiClient.get<Paginated<JobOut>>(`/companies/${companyId}/jobs`, { params }).then((r) => r.data),

  me: () => apiClient.get<CompanyDetail>('/companies/me').then((r) => r.data),

  updateMe: (body: CompanyUpdate) =>
    apiClient.patch<CompanyDetail>('/companies/me', body).then((r) => r.data),
}
