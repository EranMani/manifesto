import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import Sidebar from './components/Sidebar'
import { useAuthStore } from './store/auth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import VendorList from './pages/VendorList'
import VendorDetail from './pages/VendorDetail'
import Assistant from './pages/Assistant'
import Admin from './pages/Admin'
import ProductList from './pages/ProductList'
import ProductDetail from './pages/ProductDetail'
import ClientList from './pages/ClientList'
import ClientDetail from './pages/ClientDetail'

function RootRedirect() {
  const token = useAuthStore((state) => state.token)
  return token ? <Navigate to="/assistant" replace /> : <Navigate to="/login" replace />
}

function SidebarLayout() {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<Login />} />

        {/* Root redirect */}
        <Route path="/" element={<RootRedirect />} />

        {/* Authenticated layout with sidebar */}
        <Route element={<SidebarLayout />}>
          {/* manager + admin */}
          <Route element={<ProtectedRoute allowedRoles={['manager', 'admin']} />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/vendors" element={<VendorList />} />
            <Route path="/vendors/new" element={<VendorDetail />} />
            <Route path="/vendors/:id" element={<VendorDetail />} />
            <Route path="/products" element={<ProductList />} />
            <Route path="/products/new" element={<ProductDetail />} />
            <Route path="/products/:id" element={<ProductDetail />} />
            <Route path="/clients" element={<ClientList />} />
            <Route path="/clients/new" element={<ClientDetail />} />
            <Route path="/clients/:id" element={<ClientDetail />} />
          </Route>

          {/* all authenticated roles */}
          <Route element={<ProtectedRoute allowedRoles={['manager', 'admin', 'employee']} />}>
            <Route path="/assistant" element={<Assistant />} />
          </Route>

          {/* admin only */}
          <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
            <Route path="/admin" element={<Admin />} />
          </Route>
        </Route>

        {/* legacy chat redirects */}
        <Route path="/chat/policy" element={<Navigate to="/assistant" replace />} />
        <Route path="/chat/logistics" element={<Navigate to="/assistant" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
