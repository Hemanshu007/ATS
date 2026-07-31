import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { jobsApi } from '../../api/jobs'
import { matchingApi } from '../../api/matching'
import { getErrorMessage } from '../../api/errors'
import { EmptyState, LoadingState } from '../../components/QueryState'

export function MatchesPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const [query, setQuery] = useState('')
  const [searchError, setSearchError] = useState<string | null>(null)

  const { data: job } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
  })

  const {
    data: matches,
    isLoading: matchesLoading,
    isError: matchesError,
  } = useQuery({
    queryKey: ['job-matches', jobId],
    queryFn: () => matchingApi.matches(jobId!),
    enabled: !!jobId,
  })

  const searchMutation = useMutation({
    mutationFn: () => matchingApi.search(jobId!, query),
    onError: (err) => setSearchError(getErrorMessage(err)),
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchError(null)
    if (query.trim()) searchMutation.mutate()
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <Link to="/recruiter/jobs" className="text-sm text-gray-500 hover:text-gray-700">
        ← Back to my jobs
      </Link>

      <h1 className="mt-4 mb-1 text-2xl font-semibold text-gray-900">
        Candidate matches {job ? `for ${job.title}` : ''}
      </h1>
      <p className="mb-6 text-sm text-gray-500">Advisory only — never changes application status.</p>

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-semibold text-gray-900">Ranked by resume similarity</h2>

        {matchesLoading && <LoadingState />}
        {matchesError && (
          <EmptyState label="No matches yet — the job description may still be processing, or no resumes have been parsed." />
        )}

        <ul className="space-y-3">
          {matches?.matches.map((m) => (
            <li key={m.document_id} className="rounded border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-900">
                  {(m.parsed_data as { name?: string })?.name ?? 'Candidate'}
                </span>
                <span className="text-xs text-gray-500">
                  {(m.similarity_score * 100).toFixed(1)}% match
                </span>
              </div>
              {Array.isArray((m.parsed_data as { skills?: string[] })?.skills) && (
                <p className="mt-1 text-xs text-gray-500">
                  {(m.parsed_data as { skills: string[] }).skills.join(', ')}
                </p>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold text-gray-900">Conversational search</h2>

        <form onSubmit={handleSearch} className="mb-4 flex gap-2">
          <input
            placeholder='e.g. "candidates with Python and AWS experience"'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={searchMutation.isPending}
            className="rounded bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
          >
            {searchMutation.isPending ? 'Searching…' : 'Search'}
          </button>
        </form>

        {searchError && <p className="mb-3 text-sm text-red-600">{searchError}</p>}

        <ul className="space-y-3">
          {searchMutation.data?.matches.map((m) => (
            <li key={m.document_id} className="rounded border border-gray-200 p-4">
              <p className="text-sm text-gray-700">{m.relevance_summary}</p>
              {m.supporting_evidence.length > 0 && (
                <ul className="mt-2 list-inside list-disc text-xs text-gray-500">
                  {m.supporting_evidence.map((ev, i) => (
                    <li key={i}>{ev}</li>
                  ))}
                </ul>
              )}
            </li>
          ))}
          {searchMutation.data?.matches.length === 0 && (
            <EmptyState label="No matches found for that query." />
          )}
        </ul>
      </section>
    </div>
  )
}
