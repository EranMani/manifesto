import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getProduct,
  createProduct,
  updateProduct,
  listShipments,
  type ProductCreate,
  type ProductUpdate,
  type ShipmentRead,
} from '../api/products'

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isCreate = !id

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [quantity, setQuantity] = useState(0)
  const [unit, setUnit] = useState('')
  const [shipmentId, setShipmentId] = useState('')

  const [shipments, setShipments] = useState<ShipmentRead[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const shipmentsData = await listShipments()
        setShipments(shipmentsData)

        if (!isCreate) {
          try {
            const product = await getProduct(id)
            setName(product.name)
            setDescription(product.description ?? '')
            setQuantity(product.quantity)
            setUnit(product.unit ?? '')
            setShipmentId(product.shipment_id)
          } catch {
            setNotFound(true)
          }
        } else if (shipmentsData.length > 0) {
          setShipmentId(shipmentsData[0].id)
        }
      } catch {
        setError('Failed to load data.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id, isCreate])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      if (isCreate) {
        const data: ProductCreate = {
          name,
          shipment_id: shipmentId,
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

  const noShipments = shipments.length === 0

  return (
    <div className="p-8 max-w-xl">
      <h1 className="text-2xl font-bold mb-6">{isCreate ? 'New Product' : 'Edit Product'}</h1>

      {error && <p className="text-red-600 mb-4">{error}</p>}

      {isCreate && noShipments && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-4 mb-6">
          <p className="text-yellow-800 text-sm">
            No shipments available. Create a shipment first before adding products.
          </p>
        </div>
      )}

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

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Shipment {isCreate ? '*' : '(read-only)'}
          </label>
          {isCreate ? (
            <select
              required
              value={shipmentId}
              onChange={(e) => setShipmentId(e.target.value)}
              disabled={noShipments}
              className="border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100"
            >
              {shipments.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.tracking_code} — {s.origin} → {s.destination}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              readOnly
              value={shipments.find((s) => s.id === shipmentId)?.tracking_code ?? shipmentId}
              className="border border-gray-200 rounded px-3 py-2 w-full bg-gray-50 text-gray-500"
            />
          )}
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={submitting || (isCreate && noShipments)}
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
