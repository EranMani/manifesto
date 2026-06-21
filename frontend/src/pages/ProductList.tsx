import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  listProducts,
  deleteProduct,
  type ProductRead,
} from '../api/products'

export default function ProductList() {
  const navigate = useNavigate()
  const [rows, setRows] = useState<ProductRead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    listProducts()
      .then(setRows)
      .catch(() => setError('Failed to load products.'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    if (!search) return rows
    const q = search.toLowerCase()
    return rows.filter(
      (r) =>
        r.name.toLowerCase().includes(q) ||
        (r.description?.toLowerCase().includes(q) ?? false)
    )
  }, [rows, search])

  async function handleDelete(id: string) {
    if (!window.confirm('Are you sure you want to delete this product?')) return
    try {
      await deleteProduct(id)
      setRows((prev) => prev.filter((r) => r.id !== id))
    } catch {
      setError('Failed to delete product.')
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold">Products</h1>
        <p className="text-gray-500 mt-4">Loading...</p>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Products</h1>
        <button
          onClick={() => navigate('/products/new')}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          New Product
        </button>
      </div>

      {error && <p className="text-red-600 mb-4">{error}</p>}

      {rows.length > 0 && (
        <div className="mb-5">
          <input
            type="text"
            placeholder="Search by name or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm w-80 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      )}

      {rows.length === 0 ? (
        <div className="text-gray-500">
          <p>No products yet.</p>
          <button
            onClick={() => navigate('/products/new')}
            className="text-blue-600 hover:underline mt-1"
          >
            Create your first product
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-gray-500">No products match your search.</p>
      ) : (
        <div className="overflow-x-auto border border-gray-200 rounded-lg">
          <table className="min-w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Name</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Description</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Quantity</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Unit</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Created</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-sm font-medium">{row.name}</td>
                  <td className="px-4 py-2 text-sm text-gray-500">{row.description ?? '—'}</td>
                  <td className="px-4 py-2 text-sm">{row.quantity}</td>
                  <td className="px-4 py-2 text-sm">{row.unit ?? '—'}</td>
                  <td className="px-4 py-2 text-sm text-gray-500">
                    {new Date(row.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2 text-sm">
                    <button
                      onClick={() => handleDelete(row.id)}
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
