import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { jobsApi } from '../../api/jobs'
import { applicationsApi } from '../../api/applications'
import { getErrorMessage } from '../../api/errors'
import { useToast } from '../../context/ToastContext'

export function ApplyPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { data: job } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: !!jobId,
  })

  const applyMutation = useMutation({
    mutationFn: () => applicationsApi.apply(jobId!, file!),
    onSuccess: () => {
      showToast('Application submitted.')
      navigate('/candidate/applications')
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!file) {
      setError('Please attach a PDF resume.')
      return
    }
    applyMutation.mutate()
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-10">
      <Link to={`/jobs/${jobId}`} className="text-sm text-gray-500 hover:text-gray-700">
        ← Back to job
      </Link>

      <h1 className="mt-4 text-2xl font-semibold text-gray-900">
        Apply {job ? `to ${job.title}` : ''}
      </h1>
      {job && (
        <p className="mt-1 text-sm text-gray-500">
          {job.company.name}
          {job.location ? ` · ${job.location}` : ''}
        </p>
      )}

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Resume (PDF, max 5MB)</label>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={applyMutation.isPending}
          className="w-full rounded bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
        >
          {applyMutation.isPending ? 'Submitting…' : 'Submit application'}
        </button>
      </form>
    </div>
  )
}
