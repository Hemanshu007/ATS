import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { applicationsApi } from '../../api/applications'
import { StatusBadge } from '../../components/StatusBadge'
import { ErrorState, LoadingState } from '../../components/QueryState'

export function CandidateApplicationDetailPage() {
  const { appId } = useParams<{ appId: string }>()

  const { data: app, isLoading, isError } = useQuery({
    queryKey: ['application', appId],
    queryFn: () => applicationsApi.detail(appId!),
    enabled: !!appId,
  })

  if (isLoading) return <LoadingState />
  if (isError || !app) return <ErrorState label="Application not found." />

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <Link to="/candidate/applications" className="text-sm text-gray-500 hover:text-gray-700">
        ← Back to applications
      </Link>

      <div className="mt-4 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{app.job.title}</h1>
          <p className="mt-1 text-sm text-gray-500">
            {app.job.company} · {app.job.job_type}
          </p>
        </div>
        <StatusBadge status={app.current_status} />
      </div>

      <p className="mt-2 text-xs text-gray-400">
        Applied {new Date(app.applied_at).toLocaleDateString()}
      </p>

      {app.interview_rounds.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 text-sm font-semibold text-gray-900">Interview rounds</h2>
          <ul className="space-y-2">
            {app.interview_rounds.map((round) => (
              <li
                key={round.round_number}
                className="flex items-center justify-between rounded border border-gray-200 px-3 py-2 text-sm"
              >
                <span>
                  Round {round.round_number}
                  {round.scheduled_at && (
                    <span className="ml-2 text-gray-400">
                      {new Date(round.scheduled_at).toLocaleString()}
                    </span>
                  )}
                </span>
                <StatusBadge status={round.outcome} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-8">
        <h2 className="mb-3 text-sm font-semibold text-gray-900">Status history</h2>
        <ul className="space-y-2">
          {app.status_history.map((h, i) => (
            <li key={i} className="flex items-center justify-between text-sm">
              <StatusBadge status={h.status} />
              <span className="text-gray-400">{new Date(h.changed_at).toLocaleString()}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
