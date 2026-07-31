import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { applicationsApi } from '../../api/applications'
import { jobsApi } from '../../api/jobs'
import { StatusBadge } from '../../components/StatusBadge'
import { EmptyState, LoadingState } from '../../components/QueryState'
import type { ApplicationOut } from '../../types/application'

function ApplicationRow({ application }: { application: ApplicationOut }) {
  const { data: job } = useQuery({
    queryKey: ['job', application.job_id],
    queryFn: () => jobsApi.get(application.job_id),
  })

  return (
    <Link
      to={`/candidate/applications/${application.id}`}
      className="block rounded border border-gray-200 p-4 hover:border-gray-400"
    >
      <div className="flex items-center justify-between">
        <h2 className="font-medium text-gray-900">{job?.title ?? 'Loading…'}</h2>
        <StatusBadge status={application.current_status} />
      </div>
      <p className="mt-1 text-sm text-gray-500">
        {job?.company.name} · Applied {new Date(application.applied_at).toLocaleDateString()}
      </p>
    </Link>
  )
}

export function MyApplicationsPage() {
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['my-applications', page],
    queryFn: () => applicationsApi.myApplications({ page, page_size: 10 }),
  })

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">My applications</h1>

      {isLoading && <LoadingState />}
      {data && data.items.length === 0 && (
        <EmptyState
          label={
            <>
              You haven't applied to any jobs yet.{' '}
              <Link to="/jobs" className="underline">
                Browse open positions
              </Link>
              .
            </>
          }
        />
      )}

      <ul className="space-y-3">
        {data?.items.map((app) => (
          <li key={app.id}>
            <ApplicationRow application={app} />
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
