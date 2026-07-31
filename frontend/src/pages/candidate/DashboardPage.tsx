import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { candidatesApi } from '../../api/candidates'
import { StatusBadge } from '../../components/StatusBadge'
import { EmptyState, LoadingState } from '../../components/QueryState'

export function CandidateDashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['candidate-dashboard'],
    queryFn: candidatesApi.dashboard,
  })

  if (isLoading) return <LoadingState />
  if (!data) return null

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">Dashboard</h1>

      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="rounded border border-gray-200 p-4 text-center">
          <p className="text-2xl font-semibold text-gray-900">{data.total_applications}</p>
          <p className="text-xs text-gray-500">Total applications</p>
        </div>
        {Object.entries(data.status_breakdown).map(([status, count]) => (
          <div key={status} className="rounded border border-gray-200 p-4 text-center">
            <p className="text-2xl font-semibold text-gray-900">{count}</p>
            <p className="text-xs capitalize text-gray-500">{status}</p>
          </div>
        ))}
      </div>

      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Recent applications</h2>
        <Link to="/candidate/applications" className="text-xs text-gray-500 underline">
          View all
        </Link>
      </div>

      {data.recent_applications.length === 0 && <EmptyState label="No applications yet." />}

      <ul className="space-y-2">
        {data.recent_applications.map((app, i) => (
          <li
            key={i}
            className="flex items-center justify-between rounded border border-gray-200 px-3 py-2"
          >
            <div>
              <p className="text-sm font-medium text-gray-900">{app.job_title}</p>
              <p className="text-xs text-gray-500">{app.company_name}</p>
            </div>
            <StatusBadge status={app.current_status} />
          </li>
        ))}
      </ul>
    </div>
  )
}
