import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../store/auth'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', roles: ['manager', 'admin'] },
  { to: '/products', label: 'Products', roles: ['manager', 'admin'] },
  { to: '/vendors', label: 'Vendors', roles: ['manager', 'admin'] },
  { to: '/assistant', label: 'Assistant', roles: ['manager', 'admin', 'employee'] },
  { to: '/admin', label: 'Admin', roles: ['admin'] },
]

export default function Sidebar() {
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  const visibleItems = navItems.filter(
    (item) => user && item.roles.includes(user.role)
  )

  return (
    <aside className="w-56 bg-gray-900 text-gray-300 flex flex-col min-h-screen">
      <div className="px-4 py-5 text-white font-bold text-lg border-b border-gray-700">
        Manifesto
      </div>

      <nav className="flex-1 py-4">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `block px-4 py-2 text-sm hover:bg-gray-800 hover:text-white ${
                isActive ? 'bg-gray-800 text-white font-medium' : ''
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-gray-700 px-4 py-3">
        <div className="text-xs text-gray-500 mb-2">{user?.name}</div>
        <button
          onClick={logout}
          className="text-sm text-gray-400 hover:text-white"
        >
          Sign out
        </button>
      </div>
    </aside>
  )
}
