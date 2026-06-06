import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import { useAuthStore } from './store/auth'

// Inline stub pages — real pages land in a later commit
const Login = () => <div>Login</div>
const Dashboard = () => <div>Coming soon</div>
const Vendors = () => <div>Coming soon</div>
const VendorDetail = () => <div>Coming soon</div>
const ChatPolicy = () => <div>Coming soon</div>
const ChatLogistics = () => <div>Coming soon</div>
const Admin = () => <div>Coming soon</div>

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
          <Route path="/vendors" element={<Vendors />} />
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
