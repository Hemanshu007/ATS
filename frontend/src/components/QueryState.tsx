import type { ReactNode } from 'react'

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-gray-500">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-gray-300 border-t-gray-600" />
      {label}
    </div>
  )
}

export function ErrorState({ label = 'Something went wrong.' }: { label?: string }) {
  return <p className="py-10 text-center text-sm text-red-600">{label}</p>
}

export function EmptyState({ label }: { label: ReactNode }) {
  return <p className="py-6 text-center text-sm text-gray-500">{label}</p>
}
