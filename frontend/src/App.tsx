import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import { useAuthStore } from './store/auth'
import Dashboard from './pages/Dashboard'
import VendorList from './pages/VendorList'
import VendorDetail from './pages/VendorDetail'
import ChatPolicy from './pages/ChatPolicy'
import ChatLogistics from './pages/ChatLogistics'
import Admin from './pages/Admin'

// Inline stub — real Login page built in C20
const Login = () => <div>Login</div>

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
          <Route path="/chat/logistics" element={<ChatLogistics />} />
        </Route>

        {/* manager + admin + employee */}
        <Route element={<ProtectedRoute allowedRoles={['manager', 'admin', 'employee']} />}>
          <Route path="/chat/policy" element={<ChatPolicy />} />
        </Route>

        {/* admin only */}
        <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
          <Route path="/admin" element={<Admin />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
