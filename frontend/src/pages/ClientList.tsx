import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listClients, deleteClient, type ClientRead } from '../api/products'
import { AxiosError } from 'axios'

export default function ClientList() {
  const navigate = useNavigate()
  const [clients, setClients] = useState<ClientRead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    listClients()
      .then(setClients)
      .catch(() => setError('Failed to load clients.'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    if (!search) return clients
    const q = search.toLowerCase()
    return clients.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        (c.email?.toLowerCase().includes(q) ?? false) ||
        (c.country?.toLowerCase().includes(q) ?? false)
    )
  }, [clients, search])

  async function handleDelete(id: string) {
    if (!window.confirm('Are you sure you want to delete this client?')) return
    try {
      await deleteClient(id)
      setClients((prev) => prev.filter((c) => c.id !== id))
    } catch (err) {
      if (err instanceof AxiosError && err.response?.status === 409) {
        const detail = err.response.data?.detail ?? 'Client has associated shipments and cannot be deleted.'
        setError(String(detail))
      } else {
        setError('Failed to delete client.')
      }
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold">Clients</h1>
        <p className="text-gray-500 mt-4">Loading...</p>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Clients</h1>
        <button
          onClick={() => navigate('/clients/new')}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          New Client
        </button>
      </div>

      {error && <p className="text-red-600 mb-4">{error}</p>}

      {clients.length > 0 && (
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

      {clients.length === 0 ? (
        <div className="text-gray-500">
          <p>No clients yet.</p>
          <button
            onClick={() => navigate('/clients/new')}
            className="text-blue-600 hover:underline mt-1"
          >
            Create your first client
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-gray-500">No clients match your search.</p>
      ) : (
        <div className="overflow-x-auto border border-gray-200 rounded-lg">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Badge</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Name</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Contact</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Email</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Country</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Created</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((c) => (
                <tr
                  key={c.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/clients/${c.id}`)}
                >
                  <td className="px-4 py-2">
                    <span
                      className="inline-block w-4 h-4 rounded-full"
                      style={{ backgroundColor: c.badge_color }}
                    />
                  </td>
                  <td className="px-4 py-2 text-sm font-medium">{c.name}</td>
                  <td className="px-4 py-2 text-sm text-gray-500">{c.contact ?? '—'}</td>
                  <td className="px-4 py-2 text-sm text-gray-500">{c.email ?? '—'}</td>
                  <td className="px-4 py-2 text-sm text-gray-500">{c.country ?? '—'}</td>
                  <td className="px-4 py-2 text-sm text-gray-500">
                    {new Date(c.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDelete(c.id)
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
