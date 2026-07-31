# ATS Frontend

React + TypeScript + Vite + Tailwind CSS single-page app for the [ATS backend](../README.md) — role-based candidate and recruiter portals consuming the FastAPI API.

## Stack

- **Vite + React 19 + TypeScript**
- **React Router** — role-gated routing (`/candidate/*`, `/recruiter/*`)
- **TanStack Query** — server state, caching, loading/error states
- **Axios** — typed API client with JWT attach + refresh-on-401 (queues concurrent 401s behind a single refresh)
- **Tailwind CSS** — utility-first styling, no component library

## Setup

```bash
cp .env.example .env   # set VITE_API_URL to your backend (defaults to http://localhost:8000)
npm install
npm run dev             # http://localhost:5173
```

The backend must be running (see the [root README](../README.md#quick-start)) and its `CORS_ORIGINS` must include this dev server's origin.

## Structure

```
src/
├── api/                 # Axios client + one typed request module per backend router
│   ├── client.ts         # Axios instance, JWT interceptor, refresh-on-401
│   └── tokenStorage.ts   # localStorage token persistence
├── context/
│   ├── AuthContext.tsx    # login/register/logout/me, session restore on load
│   └── ToastContext.tsx   # toast notifications
├── components/           # Navbar, ProtectedRoute, CandidateLayout/RecruiterLayout, StatusBadge, QueryState
├── pages/
│   ├── candidate/          # Apply, My Applications, Application Detail, Profile, Dashboard
│   └── recruiter/          # Dashboard, My Jobs, Job Applications, Application Detail, Matches/Search
├── types/                 # TypeScript types mirroring the backend's Pydantic schemas
└── constants/             # Application status-transition state machine (mirrors backend)
```

## Available Scripts

```bash
npm run dev        # start dev server
npm run build      # type-check (tsc -b) + production build
npm run preview    # preview the production build locally
npm run lint        # oxlint
```

## Notes

- Auth tokens are stored in `localStorage`; the Axios response interceptor automatically retries a request once with a refreshed token on `401`, and logs the user out if the refresh itself fails.
- `src/constants/statusTransitions.ts` mirrors the backend's application status state machine so the UI only ever offers valid next statuses — kept in sync manually with `app/core/constants.py`.
- Resume download handles both response shapes the backend can return (a raw PDF stream for local storage, or a JSON envelope with a presigned S3 URL) transparently.
