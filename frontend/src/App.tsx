import { Route, Routes } from 'react-router-dom'
import { Navbar } from './components/Navbar'
import { ProtectedRoute } from './components/ProtectedRoute'
import { CandidateLayout } from './components/CandidateLayout'
import { RecruiterLayout } from './components/RecruiterLayout'
import { HomePage } from './pages/HomePage'
import { JobsPage } from './pages/JobsPage'
import { JobDetailPage } from './pages/JobDetailPage'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { ApplyPage } from './pages/candidate/ApplyPage'
import { MyApplicationsPage } from './pages/candidate/MyApplicationsPage'
import { CandidateApplicationDetailPage } from './pages/candidate/ApplicationDetailPage'
import { ProfilePage } from './pages/candidate/ProfilePage'
import { CandidateDashboardPage } from './pages/candidate/DashboardPage'
import { RecruiterDashboardPage } from './pages/recruiter/DashboardPage'
import { MyJobsPage } from './pages/recruiter/MyJobsPage'
import { JobApplicationsPage } from './pages/recruiter/JobApplicationsPage'
import { RecruiterApplicationDetailPage } from './pages/recruiter/ApplicationDetailPage'
import { MatchesPage } from './pages/recruiter/MatchesPage'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route
          path="/jobs/:jobId/apply"
          element={
            <ProtectedRoute role="candidate">
              <ApplyPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/candidate"
          element={
            <ProtectedRoute role="candidate">
              <CandidateLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<CandidateDashboardPage />} />
          <Route path="applications" element={<MyApplicationsPage />} />
          <Route path="applications/:appId" element={<CandidateApplicationDetailPage />} />
          <Route path="profile" element={<ProfilePage />} />
        </Route>

        <Route
          path="/recruiter"
          element={
            <ProtectedRoute role="recruiter">
              <RecruiterLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<RecruiterDashboardPage />} />
          <Route path="jobs" element={<MyJobsPage />} />
        </Route>

        <Route
          path="/recruiter/jobs/:jobId/applications"
          element={
            <ProtectedRoute role="recruiter">
              <JobApplicationsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/recruiter/jobs/:jobId/matches"
          element={
            <ProtectedRoute role="recruiter">
              <MatchesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/recruiter/applications/:appId"
          element={
            <ProtectedRoute role="recruiter">
              <RecruiterApplicationDetailPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </div>
  )
}

export default App
