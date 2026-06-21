import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getVendor,
  createVendor,
  updateVendor,
  type VendorCreate,
  type VendorUpdate,
} from '../api/products'

export default function VendorDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isCreate = !id

  const [name, setName] = useState('')
  const [contact, setContact] = useState('')
  const [email, setEmail] = useState('')
  const [country, setCountry] = useState('')

  const [loading, setLoading] = useState(!isCreate)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (isCreate) return
    getVendor(id)
      .then((vendor) => {
        setName(vendor.name)
        setContact(vendor.contact ?? '')
        setEmail(vendor.email ?? '')
        setCountry(vendor.country ?? '')
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
        const data: VendorCreate = {
          name,
          contact: contact || null,
          email: email || null,
          country: country || null,
        }
        await createVendor(data)
      } else {
        const data: VendorUpdate = {
          name: name || null,
          contact: contact || null,
          email: email || null,
          country: country || null,
        }
        await updateVendor(id, data)
      }
      navigate('/vendors')
    } catch {
      setError(isCreate ? 'Failed to create vendor.' : 'Failed to update vendor.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold">{isCreate ? 'New Vendor' : 'Edit Vendor'}</h1>
        <p className="text-gray-500 mt-4">Loading...</p>
      </div>
    )
  }

  if (notFound) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold">Vendor not found</h1>
        <button
          onClick={() => navigate('/vendors')}
          className="text-blue-600 hover:underline mt-2"
        >
          Back to vendors
        </button>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-xl">
      <h1 className="text-2xl font-bold mb-6">{isCreate ? 'New Vendor' : 'Edit Vendor'}</h1>

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
          <label className="block text-sm font-medium text-gray-700 mb-1">Contact</label>
          <input
            type="text"
            value={contact}
            onChange={(e) => setContact(e.target.value)}
            className="border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
          <input
            type="text"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            className="border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={submitting}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Saving...' : isCreate ? 'Create Vendor' : 'Save Changes'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/vendors')}
            className="border border-gray-300 px-4 py-2 rounded hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
