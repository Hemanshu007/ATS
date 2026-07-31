import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { tokenStorage, emitAuthLogout } from './tokenStorage'

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_URL,
})

apiClient.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Requests that 401 while a refresh is already in flight get queued here and
// retried once the new access token lands, instead of each firing its own refresh.
let isRefreshing = false
let pendingQueue: {
  resolve: (token: string) => void
  reject: (error: unknown) => void
}[] = []

function flushQueue(error: unknown, token: string | null) {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (token) resolve(token)
    else reject(error)
  })
  pendingQueue = []
}

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retried?: boolean
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetriableConfig | undefined
    const status = error.response?.status
    const url = originalRequest?.url ?? ''

    const isAuthEndpoint =
      url.includes('/auth/login') || url.includes('/auth/register') || url.includes('/auth/refresh')

    if (status !== 401 || !originalRequest || originalRequest._retried || isAuthEndpoint) {
      return Promise.reject(error)
    }

    const refreshToken = tokenStorage.getRefreshToken()
    if (!refreshToken) {
      tokenStorage.clear()
      emitAuthLogout()
      return Promise.reject(error)
    }

    originalRequest._retried = true

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingQueue.push({
          resolve: (token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(apiClient(originalRequest))
          },
          reject,
        })
      })
    }

    isRefreshing = true
    try {
      const { data } = await axios.post(`${API_URL}/auth/refresh`, { refresh_token: refreshToken })
      tokenStorage.setTokens(data.access_token, data.refresh_token, data.role)
      flushQueue(null, data.access_token)
      originalRequest.headers.Authorization = `Bearer ${data.access_token}`
      return apiClient(originalRequest)
    } catch (refreshError) {
      flushQueue(refreshError, null)
      tokenStorage.clear()
      emitAuthLogout()
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  },
)
