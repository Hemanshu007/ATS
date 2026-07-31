import { NavLink, Outlet } from 'react-router-dom'

const tabClass = ({ isActive }: { isActive: boolean }) =>
  `border-b-2 px-1 py-3 text-sm ${
    isActive ? 'border-gray-900 font-medium text-gray-900' : 'border-transparent text-gray-500'
  }`

export function CandidateLayout() {
  return (
    <div>
      <div className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-2xl gap-6 px-4">
          <NavLink to="/candidate" end className={tabClass}>
            Dashboard
          </NavLink>
          <NavLink to="/candidate/applications" className={tabClass}>
            Applications
          </NavLink>
          <NavLink to="/candidate/profile" className={tabClass}>
            Profile
          </NavLink>
        </div>
      </div>
      <Outlet />
    </div>
  )
}
