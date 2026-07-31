import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { applicationsApi } from '../../api/applications'
import { jobsApi } from '../../api/jobs'
import { StatusBadge } from '../../components/StatusBadge'
import { EmptyState, LoadingState } from '../../components/QueryState'
import type { ApplicationStatus } from '../../types/application'

const STATUSES: ApplicationStatus[] = [
  'applied',
  'screening',
  'interview',
  'offer',
  'hired',
  'rejected',
]

export function JobApplicationsPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<ApplicationStatus | ''>('')

  const { data: job } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
  })

  const { data, isLoading } = useQuery({
    queryKey: ['job-applications', jobId, page, status],
    queryFn: () =>
      applicationsApi.forJob(jobId!, { page, page_size: 10, status: status || undefined }),
    enabled: !!jobId,
  })

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link to="/recruiter/jobs" className="text-sm text-gray-500 hover:text-gray-700">
        ← Back to my jobs
      </Link>

      <h1 className="mt-4 mb-6 text-2xl font-semibold text-gray-900">
        Applications {job ? `for ${job.title}` : ''}
      </h1>

      <select
        value={status}
        onChange={(e) => {
          setPage(1)
          setStatus(e.target.value as ApplicationStatus | '')
        }}
        className="mb-6 rounded border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="">All statuses</option>
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      {isLoading && <LoadingState />}
      {data && data.items.length === 0 && (
        <EmptyState label="No applications match this filter." />
      )}

      <ul className="space-y-3">
        {data?.items.map((app) => (
          <li key={app.id}>
            <Link
              to={`/recruiter/applications/${app.id}`}
              className="flex items-center justify-between rounded border border-gray-200 p-4 hover:border-gray-400"
            >
              <span className="text-sm text-gray-700">
                Applied {new Date(app.applied_at).toLocaleDateString()}
              </span>
              <StatusBadge status={app.current_status} />
            </Link>
          </li>
        ))}
      </ul>

      {data && data.total_pages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-4 text-sm">
          <button
            disabled={!data.has_previous}
            onClick={() => setPage((p) => p - 1)}
            className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-gray-500">
            Page {data.page} of {data.total_pages}
          </span>
          <button
            disabled={!data.has_next}
            onClick={() => setPage((p) => p + 1)}
            className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
