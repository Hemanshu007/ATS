import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { jobsApi } from '../api/jobs'
import { EmptyState, ErrorState, LoadingState } from '../components/QueryState'
import type { JobType } from '../types/job'

const JOB_TYPES: JobType[] = ['onsite', 'remote', 'hybrid']

export function JobsPage() {
  const [page, setPage] = useState(1)
  const [jobType, setJobType] = useState<JobType | ''>('')
  const [location, setLocation] = useState('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['jobs', page, jobType, location],
    queryFn: () =>
      jobsApi.list({
        page,
        page_size: 10,
        job_type: jobType || undefined,
        location: location || undefined,
      }),
  })

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">Open positions</h1>

      <div className="mb-6 flex flex-wrap gap-3">
        <select
          value={jobType}
          onChange={(e) => {
            setPage(1)
            setJobType(e.target.value as JobType | '')
          }}
          className="rounded border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All types</option>
          {JOB_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>

        <input
          placeholder="Filter by location"
          value={location}
          onChange={(e) => {
            setPage(1)
            setLocation(e.target.value)
          }}
          className="rounded border border-gray-300 px-3 py-2 text-sm"
        />
      </div>

      {isLoading && <LoadingState label="Loading jobs…" />}
      {isError && <ErrorState label="Failed to load jobs." />}

      {data && data.items.length === 0 && <EmptyState label="No jobs match your filters." />}

      <ul className="space-y-3">
        {data?.items.map((job) => (
          <li key={job.id}>
            <Link
              to={`/jobs/${job.id}`}
              className="block rounded border border-gray-200 p-4 hover:border-gray-400"
            >
              <div className="flex items-center justify-between">
                <h2 className="font-medium text-gray-900">{job.title}</h2>
                <span className="text-xs uppercase text-gray-400">{job.job_type}</span>
              </div>
              <p className="mt-1 text-sm text-gray-500">
                {job.company.name}
                {job.location ? ` · ${job.location}` : ''}
              </p>
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
