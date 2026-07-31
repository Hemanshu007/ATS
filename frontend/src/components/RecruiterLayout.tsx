import { NavLink, Outlet } from 'react-router-dom'

const tabClass = ({ isActive }: { isActive: boolean }) =>
  `border-b-2 px-1 py-3 text-sm ${
    isActive ? 'border-gray-900 font-medium text-gray-900' : 'border-transparent text-gray-500'
  }`

export function RecruiterLayout() {
  return (
    <div>
      <div className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-3xl gap-6 px-4">
          <NavLink to="/recruiter" end className={tabClass}>
            Dashboard
          </NavLink>
          <NavLink to="/recruiter/jobs" className={tabClass}>
            My Jobs
          </NavLink>
        </div>
      </div>
      <Outlet />
    </div>
  )
}
