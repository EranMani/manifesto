import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listVendors, deleteVendor, type VendorRead } from '../api/products'
import { AxiosError } from 'axios'

export default function VendorList() {
  const navigate = useNavigate()
  const [vendors, setVendors] = useState<VendorRead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    listVendors()
      .then(setVendors)
      .catch(() => setError('Failed to load vendors.'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    if (!search) return vendors
    const q = search.toLowerCase()
    return vendors.filter(
      (v) =>
        v.name.toLowerCase().includes(q) ||
        (v.email?.toLowerCase().includes(q) ?? false) ||
        (v.country?.toLowerCase().includes(q) ?? false)
    )
  }, [vendors, search])

  async function handleDelete(id: string) {
    if (!window.confirm('Are you sure you want to delete this vendor?')) return
    try {
      await deleteVendor(id)
      setVendors((prev) => prev.filter((v) => v.id !== id))
    } catch (err) {
      if (err instanceof AxiosError && err.response?.status === 409) {
        const detail = err.response.data?.detail ?? 'Vendor has associated shipments and cannot be deleted.'
        setError(String(detail))
      } else {
        setError('Failed to delete vendor.')
      }
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold">Vendors</h1>
        <p className="text-gray-500 mt-4">Loading...</p>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Vendors</h1>
        <button
          onClick={() => navigate('/vendors/new')}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          New Vendor
        </button>
      </div>

      {error && <p className="text-red-600 mb-4">{error}</p>}

      {vendors.length > 0 && (
        <div className="mb-5">
          <input
            type="text"
            placeholder="Search by name, email, or country..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm w-80 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      )}

      {vendors.length === 0 ? (
        <div className="text-gray-500">
          <p>No vendors yet.</p>
          <button
            onClick={() => navigate('/vendors/new')}
            className="text-blue-600 hover:underline mt-1"
          >
            Create your first vendor
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-gray-500">No vendors match your search.</p>
      ) : (
        <div className="overflow-x-auto border border-gray-200 rounded-lg">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Name</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Contact</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Email</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Country</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Created</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((v) => (
                <tr
                  key={v.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/vendors/${v.id}`)}
                >
                  <td className="px-4 py-2 text-sm font-medium">{v.name}</td>
                  <td className="px-4 py-2 text-sm text-gray-500">{v.contact ?? '—'}</td>
                  <td className="px-4 py-2 text-sm text-gray-500">{v.email ?? '—'}</td>
                  <td className="px-4 py-2 text-sm text-gray-500">{v.country ?? '—'}</td>
                  <td className="px-4 py-2 text-sm text-gray-500">
                    {new Date(v.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDelete(v.id)
                      }}
                      className="text-red-600 hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
