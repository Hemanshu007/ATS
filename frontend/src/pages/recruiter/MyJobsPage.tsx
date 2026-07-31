import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { recruitersApi } from '../../api/recruiters'
import { jobsApi } from '../../api/jobs'
import { getErrorMessage } from '../../api/errors'
import { useToast } from '../../context/ToastContext'
import { LoadingState } from '../../components/QueryState'
import type { JobType } from '../../types/job'

function CreateJobForm({ onCreated }: { onCreated: () => void }) {
  const { showToast } = useToast()
  const [isOpen, setIsOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [location, setLocation] = useState('')
  const [jobType, setJobType] = useState<JobType>('onsite')
  const [error, setError] = useState<string | null>(null)

  const createMutation = useMutation({
    mutationFn: () => jobsApi.create({ title, description, location, job_type: jobType }),
    onSuccess: () => {
      setTitle('')
      setDescription('')
      setLocation('')
      setIsOpen(false)
      showToast('Job posted.')
      onCreated()
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    createMutation.mutate()
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="mb-6 rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
      >
        + Post a job
      </button>
    )
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mb-6 space-y-3 rounded border border-gray-200 p-4"
    >
      <input
        required
        placeholder="Job title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
      />
      <textarea
        required
        placeholder="Description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        rows={4}
        className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
      />
      <div className="flex gap-3">
        <input
          placeholder="Location"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
        />
        <select
          value={jobType}
          onChange={(e) => setJobType(e.target.value as JobType)}
          className="rounded border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="onsite">onsite</option>
          <option value="remote">remote</option>
          <option value="hybrid">hybrid</option>
        </select>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={createMutation.isPending}
          className="rounded bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
        >
          {createMutation.isPending ? 'Posting…' : 'Post job'}
        </button>
        <button
          type="button"
          onClick={() => setIsOpen(false)}
          className="rounded border border-gray-300 px-3 py-2 text-sm text-gray-600"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

export function MyJobsPage() {
  const [page, setPage] = useState(1)
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const { data, isLoading } = useQuery({
    queryKey: ['recruiter-jobs', page],
    queryFn: () => recruitersApi.myJobs({ page, page_size: 10 }),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['recruiter-jobs'] })

  const toggleStatusMutation = useMutation({
    mutationFn: ({ jobId, status }: { jobId: string; status: 'open' | 'closed' }) =>
      jobsApi.updateStatus(jobId, { status }),
    onSuccess: (_data, variables) => {
      showToast(variables.status === 'open' ? 'Job reopened.' : 'Job closed.')
      invalidate()
    },
    onError: (err) => showToast(getErrorMessage(err), 'error'),
  })

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="mb-6 text-2xl font-semibold text-gray-900">My jobs</h1>

      <CreateJobForm onCreated={invalidate} />

      {isLoading && <LoadingState />}

      <ul className="space-y-3">
        {data?.items.map((job) => (
          <li key={job.id} className="rounded border border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-medium text-gray-900">{job.title}</h2>
                <p className="mt-1 text-xs text-gray-500">
                  {job.job_type} · {job.application_count} application
                  {job.application_count === 1 ? '' : 's'}
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

            <div className="mt-3 flex flex-wrap gap-3 text-sm">
              <Link to={`/recruiter/jobs/${job.id}/applications`} className="text-gray-700 underline">
                View applications
              </Link>
              <Link to={`/recruiter/jobs/${job.id}/matches`} className="text-gray-700 underline">
                Candidate matches
              </Link>
              <button
                onClick={() =>
                  toggleStatusMutation.mutate({
                    jobId: job.id,
                    status: job.status === 'open' ? 'closed' : 'open',
                  })
                }
                className="text-gray-700 underline"
              >
                {job.status === 'open' ? 'Close job' : 'Reopen job'}
              </button>
            </div>
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
