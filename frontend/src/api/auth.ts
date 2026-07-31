import { apiClient } from './client'
import type { LoginRequest, RegisterRequest, TokenResponse, MeResponse } from '../types/auth'

export const authApi = {
  register: (body: RegisterRequest) =>
    apiClient.post<TokenResponse>('/auth/register', body).then((r) => r.data),

  login: (body: LoginRequest) =>
    apiClient.post<TokenResponse>('/auth/login', body).then((r) => r.data),

  me: () => apiClient.get<MeResponse>('/auth/me').then((r) => r.data),
}
