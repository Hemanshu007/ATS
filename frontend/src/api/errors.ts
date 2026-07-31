import { isAxiosError } from 'axios'

/** FastAPI error bodies are usually {detail: string} but validation errors are {detail: [{msg, loc}, ...]}. */
export function getErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((d) => d.msg ?? JSON.stringify(d)).join(', ')
    }
    if (error.message) return error.message
  }
  return 'Something went wrong. Please try again.'
}
