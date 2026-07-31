import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { jobsApi } from '../api/jobs'
import { useAuth } from '../context/AuthContext'
import { ErrorState, LoadingState } from '../components/QueryState'

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const { isAuthenticated, user } = useAuth()

  const { data: job, isLoading, isError } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
  })

  if (isLoading) return <LoadingState />
  if (isError || !job) return <ErrorState label="Job not found." />

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <Link to="/jobs" className="text-sm text-gray-500 hover:text-gray-700">
        ← Back to jobs
      </Link>

      <div className="mt-4 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{job.title}</h1>
          <p className="mt-1 text-sm text-gray-500">
            {job.company.name}
            {job.location ? ` · ${job.location}` : ''} · {job.job_type}
          </p>
        </div>
        <span
          className={`rounded px-2 py-1 text-xs font-medium ${
            job.status === 'open' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
          }`}
        >
          {job.status}
        </span>
      </div>

      <p className="mt-6 whitespace-pre-wrap text-sm text-gray-700">{job.description}</p>

      <div className="mt-8">
        {!isAuthenticated && (
          <Link
            to="/login"
            className="inline-block rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
          >
            Log in to apply
          </Link>
        )}

        {isAuthenticated && user?.role === 'candidate' && job.status === 'open' && (
          <Link
            to={`/jobs/${job.id}/apply`}
            className="inline-block rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
          >
            Apply now
          </Link>
        )}

        {isAuthenticated && user?.role === 'candidate' && job.status !== 'open' && (
          <p className="text-sm text-gray-500">This job is closed and no longer accepting applications.</p>
        )}
      </div>
    </div>
  )
}
