import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/auth'

interface ProtectedRouteProps {
  allowedRoles: string[]
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const token = useAuthStore((state) => state.token)
  const user = useAuthStore((state) => state.user)

  if (!token) {
    return <Navigate to="/login" replace />
  }

  if (!user || !allowedRoles.includes(user.role)) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
