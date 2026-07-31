import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { applicationsApi } from '../../api/applications'
import { interviewsApi } from '../../api/interviews'
import { StatusBadge } from '../../components/StatusBadge'
import { EmptyState, ErrorState, LoadingState } from '../../components/QueryState'
import { getErrorMessage } from '../../api/errors'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { ALLOWED_STATUS_TRANSITIONS } from '../../constants/statusTransitions'
import type { ApplicationStatus } from '../../types/application'
import type { RecruiterProfileOut } from '../../types/auth'

function StatusUpdateForm({ appId, currentStatus }: { appId: string; currentStatus: ApplicationStatus }) {
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const allowed = ALLOWED_STATUS_TRANSITIONS[currentStatus]
  const [nextStatus, setNextStatus] = useState<ApplicationStatus | ''>('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () =>
      applicationsApi.updateStatus(appId, { status: nextStatus as ApplicationStatus, notes: notes || undefined }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['application', appId] })
      showToast(`Status changed to ${updated.current_status}.`)
      setNextStatus('')
      setNotes('')
      setError(null)
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  if (allowed.length === 0) {
    return <p className="text-sm text-gray-500">This application is in a terminal state.</p>
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!nextStatus) return
    mutation.mutate()
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-start gap-2">
      <select
        value={nextStatus}
        onChange={(e) => setNextStatus(e.target.value as ApplicationStatus)}
        className="rounded border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="">Change status to…</option>
        {allowed.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      <input
        placeholder="Notes (optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        className="min-w-[200px] flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
      />
      <button
        type="submit"
        disabled={!nextStatus || mutation.isPending}
        className="rounded bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
      >
        Update
      </button>
      {error && <p className="w-full text-sm text-red-600">{error}</p>}
    </form>
  )
}

function NotesSection({ appId }: { appId: string }) {
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const [content, setContent] = useState('')

  const { data: notes } = useQuery({
    queryKey: ['application-notes', appId],
    queryFn: () => applicationsApi.listNotes(appId),
  })

  const createMutation = useMutation({
    mutationFn: () => applicationsApi.createNote(appId, { content }),
    onSuccess: () => {
      setContent('')
      showToast('Note added.')
      queryClient.invalidateQueries({ queryKey: ['application-notes', appId] })
    },
    onError: (err) => showToast(getErrorMessage(err), 'error'),
  })

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-sm font-semibold text-gray-900">Internal notes</h2>

      <ul className="mb-3 space-y-2">
        {notes?.map((note) => (
          <li key={note.id} className="rounded border border-gray-200 p-3 text-sm">
            <p className="text-gray-700">{note.content}</p>
            <p className="mt-1 text-xs text-gray-400">
              {new Date(note.created_at).toLocaleString()}
            </p>
          </li>
        ))}
        {notes?.length === 0 && <EmptyState label="No notes yet." />}
      </ul>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (content.trim()) createMutation.mutate()
        }}
        className="flex gap-2"
      >
        <input
          placeholder="Add a note…"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={createMutation.isPending}
          className="rounded border border-gray-300 px-3 py-2 text-sm text-gray-700 disabled:opacity-50"
        >
          Add
        </button>
      </form>
    </section>
  )
}

function InterviewsSection({ appId }: { appId: string }) {
  const queryClient = useQueryClient()
  const { profile } = useAuth()
  const { showToast } = useToast()
  const recruiterId = (profile as RecruiterProfileOut | null)?.id

  const [roundNumber, setRoundNumber] = useState(1)
  const [scheduledAt, setScheduledAt] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: rounds } = useQuery({
    queryKey: ['interviews', appId],
    queryFn: () => interviewsApi.forApplication(appId),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['interviews', appId] })

  const createMutation = useMutation({
    mutationFn: () =>
      interviewsApi.create({
        application_id: appId,
        round_number: roundNumber,
        scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : null,
        conducted_by: recruiterId,
      }),
    onSuccess: () => {
      setScheduledAt('')
      setRoundNumber((r) => r + 1)
      setError(null)
      showToast('Interview round scheduled.')
      invalidate()
    },
    onError: (err) => setError(getErrorMessage(err)),
  })

  const outcomeMutation = useMutation({
    mutationFn: ({ id, outcome }: { id: string; outcome: 'pass' | 'fail' }) =>
      interviewsApi.updateOutcome(id, { outcome }),
    onSuccess: (_data, variables) => {
      showToast(`Round marked as ${variables.outcome}.`)
      invalidate()
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (id: string) => interviewsApi.cancel(id),
    onSuccess: () => {
      showToast('Interview round cancelled.')
      invalidate()
    },
  })

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-sm font-semibold text-gray-900">Interview rounds</h2>

      <ul className="mb-4 space-y-2">
        {rounds?.map((round) => (
          <li
            key={round.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded border border-gray-200 p-3 text-sm"
          >
            <div>
              <span className="font-medium">Round {round.round_number}</span>
              {round.scheduled_at && (
                <span className="ml-2 text-gray-400">
                  {new Date(round.scheduled_at).toLocaleString()}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge status={round.outcome} />
              {round.outcome === 'pending' && (
                <>
                  <button
                    onClick={() => outcomeMutation.mutate({ id: round.id, outcome: 'pass' })}
                    className="text-xs text-green-700 underline"
                  >
                    Pass
                  </button>
                  <button
                    onClick={() => outcomeMutation.mutate({ id: round.id, outcome: 'fail' })}
                    className="text-xs text-red-700 underline"
                  >
                    Fail
                  </button>
                  <button
                    onClick={() => cancelMutation.mutate(round.id)}
                    className="text-xs text-gray-500 underline"
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>
          </li>
        ))}
        {rounds?.length === 0 && <EmptyState label="No interview rounds yet." />}
      </ul>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          createMutation.mutate()
        }}
        className="flex flex-wrap items-end gap-2"
      >
        <div>
          <label className="mb-1 block text-xs text-gray-500">Round number</label>
          <input
            type="number"
            min={1}
            max={100}
            value={roundNumber}
            onChange={(e) => setRoundNumber(Number(e.target.value))}
            className="w-24 rounded border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500">Scheduled at (optional)</label>
          <input
            type="datetime-local"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
            className="rounded border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={createMutation.isPending}
          className="rounded bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
        >
          Schedule round
        </button>
      </form>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </section>
  )
}

export function RecruiterApplicationDetailPage() {
  const { appId } = useParams<{ appId: string }>()
  const { showToast } = useToast()
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const { data: app, isLoading, isError } = useQuery({
    queryKey: ['application', appId],
    queryFn: () => applicationsApi.detail(appId!),
    enabled: !!appId,
  })

  const handleDownload = async () => {
    setDownloadError(null)
    try {
      await applicationsApi.downloadResume(appId!)
      showToast('Resume download started.')
    } catch (err) {
      setDownloadError(getErrorMessage(err))
    }
  }

  if (isLoading) return <LoadingState />
  if (isError || !app || !appId) return <ErrorState label="Application not found." />

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <Link to={`/recruiter/jobs/${app.job.id}/applications`} className="text-sm text-gray-500 hover:text-gray-700">
        ← Back to applications
      </Link>

      <div className="mt-4 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{app.candidate.name}</h1>
          <p className="mt-1 text-sm text-gray-500">
            Applied to {app.job.title} · {new Date(app.applied_at).toLocaleDateString()}
          </p>
        </div>
        <StatusBadge status={app.current_status} />
      </div>

      <button
        onClick={handleDownload}
        className="mt-4 rounded border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:border-gray-400"
      >
        Download resume
      </button>
      {downloadError && <p className="mt-2 text-sm text-red-600">{downloadError}</p>}

      <div className="mt-6 rounded border border-gray-200 p-4">
        <StatusUpdateForm appId={appId} currentStatus={app.current_status} />
      </div>

      <InterviewsSection appId={appId} />
      <NotesSection appId={appId} />
    </div>
  )
}
