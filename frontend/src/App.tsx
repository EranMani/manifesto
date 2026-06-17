import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import { useAuthStore } from './store/auth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import VendorList from './pages/VendorList'
import VendorDetail from './pages/VendorDetail'
import Assistant from './pages/Assistant'
import Admin from './pages/Admin'

function RootRedirect() {
  const token = useAuthStore((state) => state.token)
  return token ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<Login />} />

        {/* Root redirect */}
        <Route path="/" element={<RootRedirect />} />

        {/* manager + admin */}
        <Route element={<ProtectedRoute allowedRoles={['manager', 'admin']} />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/vendors" element={<VendorList />} />
          <Route path="/vendors/:id" element={<VendorDetail />} />
        </Route>

        {/* all authenticated roles */}
        <Route element={<ProtectedRoute allowedRoles={['manager', 'admin', 'employee']} />}>
          <Route path="/assistant" element={<Assistant />} />
        </Route>

        {/* legacy chat redirects */}
        <Route path="/chat/policy" element={<Navigate to="/assistant" replace />} />
        <Route path="/chat/logistics" element={<Navigate to="/assistant" replace />} />

        {/* admin only */}
        <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
          <Route path="/admin" element={<Admin />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
