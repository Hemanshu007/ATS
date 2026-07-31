import { Link } from 'react-router-dom'

export function HomePage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-24 text-center">
      <h1 className="text-3xl font-semibold text-gray-900">Find your next role</h1>
      <p className="mt-3 text-gray-600">
        Browse open positions, apply with your resume, and let AI-powered matching connect you
        with the right opportunities.
      </p>
      <Link
        to="/jobs"
        className="mt-6 inline-block rounded bg-gray-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-gray-700"
      >
        Browse jobs
      </Link>
    </div>
  )
}
