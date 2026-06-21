import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  createShipment,
  listClients,
  listProducts,
  listVendors,
  type ClientRead,
  type ProductRead,
  type ShipmentItemCreate,
  type VendorRead,
} from '../api/products'

interface LineItem {
  product: ProductRead
  quantity: number
}

export default function ShipmentForm() {
  const navigate = useNavigate()
  const [vendors, setVendors] = useState<VendorRead[]>([])
  const [clients, setClients] = useState<ClientRead[]>([])
  const [products, setProducts] = useState<ProductRead[]>([])
  const [loading, setLoading] = useState(true)
  const [trackingCode, setTrackingCode] = useState('')
  const [vendorId, setVendorId] = useState('')
  const [clientId, setClientId] = useState('')
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [dispatchedAt, setDispatchedAt] = useState('')
  const [expectedArrivalAt, setExpectedArrivalAt] = useState('')
  const [notes, setNotes] = useState('')
  const [selectedProductId, setSelectedProductId] = useState('')
  const [lineItems, setLineItems] = useState<LineItem[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([listVendors(), listClients(), listProducts()])
      .then(([v, c, p]) => { setVendors(v); setClients(c); setProducts(p) })
      .catch(() => setError('Failed to load form data.'))
      .finally(() => setLoading(false))
  }, [])

  const addedProductIds = new Set(lineItems.map((li) => li.product.id))
  const availableProducts = products.filter((p) => !addedProductIds.has(p.id) && p.quantity > 0)

  function handleAddProduct() {
    const product = products.find((p) => p.id === selectedProductId)
    if (!product) return
    setLineItems([...lineItems, { product, quantity: 1 }])
    setSelectedProductId('')
  }

  function handleRemoveItem(productId: string) {
    setLineItems(lineItems.filter((li) => li.product.id !== productId))
  }

  function handleQuantityChange(productId: string, qty: number) {
    setLineItems(lineItems.map((li) =>
      li.product.id === productId ? { ...li, quantity: qty } : li
    ))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (lineItems.length === 0) { setError('At least one product is required.'); return }
    setSubmitting(true)
    try {
      const items: ShipmentItemCreate[] = lineItems.map((li) => ({
        product_id: li.product.id, quantity: li.quantity,
      }))
      await createShipment({
        tracking_code: trackingCode, vendor_id: vendorId,
        client_id: clientId || null, origin, destination,
        dispatched_at: new Date(dispatchedAt).toISOString(),
        expected_arrival_at: new Date(expectedArrivalAt).toISOString(),
        notes: notes || null, items,
      })
      navigate('/shipments')
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string } } }).response
      setError(resp?.data?.detail || 'Failed to create shipment.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold">New Shipment</h1>
        <p className="text-gray-500 mt-4">Loading...</p>
      </div>
    )
  }

  const inputCls = "border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-1 focus:ring-blue-500"

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">New Shipment</h1>
      {error && <p className="text-red-600 mb-4">{error}</p>}

      <form onSubmit={handleSubmit} className="space-y-6">
        <section>
          <h2 className="text-lg font-semibold mb-3">Shipment Details</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tracking Code *</label>
              <input type="text" required value={trackingCode} onChange={(e) => setTrackingCode(e.target.value)} className={inputCls} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Origin *</label>
                <input type="text" required value={origin} onChange={(e) => setOrigin(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Destination *</label>
                <input type="text" required value={destination} onChange={(e) => setDestination(e.target.value)} className={inputCls} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Dispatch Date *</label>
                <input type="datetime-local" required value={dispatchedAt} onChange={(e) => setDispatchedAt(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Expected Arrival *</label>
                <input type="datetime-local" required value={expectedArrivalAt} onChange={(e) => setExpectedArrivalAt(e.target.value)} className={inputCls} />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} className={inputCls} />
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold mb-3">Parties</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Vendor *</label>
              <select required value={vendorId} onChange={(e) => setVendorId(e.target.value)} className={inputCls}>
                <option value="">Select a vendor</option>
                {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Client *</label>
              <select required value={clientId} onChange={(e) => setClientId(e.target.value)} className={inputCls}>
                <option value="">Select a client</option>
                {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold mb-3">Products</h2>
          <div className="flex gap-2 mb-4">
            <select value={selectedProductId} onChange={(e) => setSelectedProductId(e.target.value)} className={`${inputCls} flex-1`}>
              <option value="">Select a product</option>
              {availableProducts.map((p) => <option key={p.id} value={p.id}>{p.name} (stock: {p.quantity})</option>)}
            </select>
            <button type="button" onClick={handleAddProduct} disabled={!selectedProductId}
              className="bg-gray-100 border border-gray-300 px-4 py-2 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed">
              Add Product
            </button>
          </div>
          {lineItems.length === 0 ? (
            <p className="text-gray-500 text-sm">No products added yet.</p>
          ) : (
            <div className="space-y-2">
              {lineItems.map((li) => (
                <div key={li.product.id} className="flex items-center gap-3 border border-gray-200 rounded px-3 py-2">
                  <span className="flex-1 text-sm">
                    {li.product.name} <span className="text-gray-500">(available: {li.product.quantity})</span>
                  </span>
                  <input type="number" min={1} max={li.product.quantity} value={li.quantity}
                    onChange={(e) => handleQuantityChange(li.product.id, Math.min(Math.max(1, parseInt(e.target.value) || 1), li.product.quantity))}
                    className="border border-gray-300 rounded px-2 py-1 w-20 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
                  <button type="button" onClick={() => handleRemoveItem(li.product.id)} className="text-red-500 hover:text-red-700 text-sm">
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={submitting}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
            {submitting ? 'Creating...' : 'Create Shipment'}
          </button>
          <button type="button" onClick={() => navigate('/shipments')} className="border border-gray-300 px-4 py-2 rounded hover:bg-gray-50">
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
