import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getProduct,
  createProduct,
  updateProduct,
  type ProductCreate,
  type ProductUpdate,
} from '../api/products'

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isCreate = !id

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [quantity, setQuantity] = useState(0)
  const [unit, setUnit] = useState('')

  const [loading, setLoading] = useState(!isCreate)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (isCreate) return
    getProduct(id)
      .then((product) => {
        setName(product.name)
        setDescription(product.description ?? '')
        setQuantity(product.quantity)
        setUnit(product.unit ?? '')
      })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false))
  }, [id, isCreate])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      if (isCreate) {
        const data: ProductCreate = {
          name,
          description: description || null,
          quantity,
          unit: unit || null,
        }
        await createProduct(data)
      } else {
        const data: ProductUpdate = {
          name: name || null,
          description: description || null,
          quantity,
          unit: unit || null,
        }
        await updateProduct(id, data)
      }
      navigate('/products')
    } catch {
      setError(isCreate ? 'Failed to create product.' : 'Failed to update product.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold">{isCreate ? 'New Product' : 'Edit Product'}</h1>
        <p className="text-gray-500 mt-4">Loading...</p>
      </div>
    )
  }

  if (notFound) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold">Product not found</h1>
        <button
          onClick={() => navigate('/products')}
          className="text-blue-600 hover:underline mt-2"
        >
          Back to products
        </button>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-xl">
      <h1 className="text-2xl font-bold mb-6">{isCreate ? 'New Product' : 'Edit Product'}</h1>

      {error && <p className="text-red-600 mb-4">{error}</p>}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Quantity *</label>
            <input
              type="number"
              required
              min={0}
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
              className="border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Unit</label>
            <input
              type="text"
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={submitting}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Saving...' : isCreate ? 'Create Product' : 'Save Changes'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/products')}
            className="border border-gray-300 px-4 py-2 rounded hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
