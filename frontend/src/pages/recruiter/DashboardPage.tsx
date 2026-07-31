import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { recruitersApi } from '../../api/recruiters'
import { LoadingState } from '../../components/QueryState'

export function RecruiterDashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['recruiter-dashboard'],
    queryFn: recruitersApi.dashboard,
  })

  if (isLoading) return <LoadingState />
  if (!data) return null

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">Dashboard</h1>

      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded border border-gray-200 p-4 text-center">
          <p className="text-2xl font-semibold text-gray-900">{data.total_jobs}</p>
          <p className="text-xs text-gray-500">Total jobs</p>
        </div>
        <div className="rounded border border-gray-200 p-4 text-center">
          <p className="text-2xl font-semibold text-gray-900">{data.open_jobs}</p>
          <p className="text-xs text-gray-500">Open jobs</p>
        </div>
        <div className="rounded border border-gray-200 p-4 text-center">
          <p className="text-2xl font-semibold text-gray-900">{data.closed_jobs}</p>
          <p className="text-xs text-gray-500">Closed jobs</p>
        </div>
        <div className="rounded border border-gray-200 p-4 text-center">
          <p className="text-2xl font-semibold text-gray-900">{data.total_applications}</p>
          <p className="text-xs text-gray-500">Total applications</p>
        </div>
      </div>

      <h2 className="mb-3 text-sm font-semibold text-gray-900">Pipeline</h2>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
        {Object.entries(data.pipeline_summary).map(([status, count]) => (
          <div key={status} className="rounded border border-gray-200 p-3 text-center">
            <p className="text-xl font-semibold text-gray-900">{count}</p>
            <p className="text-xs capitalize text-gray-500">{status}</p>
          </div>
        ))}
      </div>

      <Link
        to="/recruiter/jobs"
        className="mt-8 inline-block rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
      >
        Manage jobs
      </Link>
    </div>
  )
}
