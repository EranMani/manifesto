import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getShipmentDetail,
  listClients,
  listShipments,
  listVendors,
  type ClientRead,
  type ShipmentDetailRead,
  type ShipmentRead,
  type VendorRead,
} from '../api/products'

const STATUSES = [
  'pending',
  'in_transit',
  'delayed',
  'delivered',
  'partial',
  'damaged',
  'cancelled',
  'returned',
  'lost',
] as const

interface ShipmentGroup {
  shipment: ShipmentRead
  vendor: VendorRead | null
  client: ClientRead | null
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [groups, setGroups] = useState<ShipmentGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [destinationFilter, setDestinationFilter] = useState('')
  const [originFilter, setOriginFilter] = useState('')
  const [vendorFilter, setVendorFilter] = useState('')
  const [clientFilter, setClientFilter] = useState('')

  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [detailCache, setDetailCache] = useState<Map<string, ShipmentDetailRead>>(new Map())
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    Promise.all([listShipments(), listVendors(), listClients()])
      .then(([shipments, vendors, clients]) => {
        const vendorMap = new Map(vendors.map((v) => [v.id, v]))
        const clientMap = new Map(clients.map((c) => [c.id, c]))

        const grouped: ShipmentGroup[] = shipments.map((s) => ({
          shipment: s,
          vendor: vendorMap.get(s.vendor_id) ?? null,
          client: s.client_id ? clientMap.get(s.client_id) ?? null : null,
        }))

        setGroups(grouped)
      })
      .catch(() => setError('Failed to load data.'))
      .finally(() => setLoading(false))
  }, [])

  const destinations = useMemo(
    () => [...new Set(groups.map((g) => g.shipment.destination))].sort(),
    [groups]
  )
  const origins = useMemo(
    () => [...new Set(groups.map((g) => g.shipment.origin))].sort(),
    [groups]
  )
  const vendors = useMemo(
    () =>
      [...new Map(groups.filter((g) => g.vendor).map((g) => [g.vendor!.id, g.vendor!.name])).entries()]
        .sort((a, b) => a[1].localeCompare(b[1])),
    [groups]
  )

  const clients = useMemo(
    () =>
      [...new Map(groups.filter((g) => g.client).map((g) => [g.client!.id, g.client!.name])).entries()]
        .sort((a, b) => a[1].localeCompare(b[1])),
    [groups]
  )

  const filteredGroups = useMemo(() => {
    const q = search.toLowerCase()
    return groups.filter((g) => {
      if (statusFilter && g.shipment.status !== statusFilter) return false
      if (destinationFilter && g.shipment.destination !== destinationFilter) return false
      if (originFilter && g.shipment.origin !== originFilter) return false
      if (vendorFilter && g.vendor?.id !== vendorFilter) return false
      if (clientFilter && g.client?.id !== clientFilter) return false
      if (q && !g.shipment.tracking_code.toLowerCase().includes(q)) return false
      return true
    })
  }, [groups, search, statusFilter, destinationFilter, originFilter, vendorFilter, clientFilter])

  const handleCardClick = (id: string) => {
    if (expandedId === id) {
      setExpandedId(null)
      return
    }
    setExpandedId(id)
    if (!detailCache.has(id)) {
      setDetailLoading(true)
      getShipmentDetail(id)
        .then((detail) => {
          setDetailCache((prev) => new Map(prev).set(id, detail))
        })
        .catch(() => {})
        .finally(() => setDetailLoading(false))
    }
  }

  const activeFilterCount = [statusFilter, destinationFilter, originFilter, vendorFilter, clientFilter, search].filter(Boolean).length

  if (loading) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold">Shipments</h1>
        <p className="text-gray-500 mt-4">Loading...</p>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Shipments</h1>
        <button
          onClick={() => navigate('/shipments/new')}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          New Shipment
        </button>
      </div>

      {error && <p className="text-red-600 mb-4">{error}</p>}

      {groups.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 mb-5">
          <input
            type="text"
            placeholder="Search tracking code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm w-52 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.replace('_', ' ')}
              </option>
            ))}
          </select>
          <select
            value={destinationFilter}
            onChange={(e) => setDestinationFilter(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All destinations</option>
            {destinations.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <select
            value={originFilter}
            onChange={(e) => setOriginFilter(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All origins</option>
            {origins.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
          <select
            value={vendorFilter}
            onChange={(e) => setVendorFilter(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All vendors</option>
            {vendors.map(([id, name]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
          <select
            value={clientFilter}
            onChange={(e) => setClientFilter(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All clients</option>
            {clients.map(([id, name]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
          {activeFilterCount > 0 && (
            <button
              onClick={() => {
                setSearch('')
                setStatusFilter('')
                setDestinationFilter('')
                setOriginFilter('')
                setVendorFilter('')
                setClientFilter('')
              }}
              className="text-sm text-gray-500 hover:text-gray-700 underline"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {groups.length === 0 ? (
        <p className="text-gray-500">No shipments yet.</p>
      ) : filteredGroups.length === 0 ? (
        <p className="text-gray-500">No shipments match the current filters.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredGroups.map((group) => {
            const isExpanded = expandedId === group.shipment.id
            const detail = detailCache.get(group.shipment.id)
            return (
            <div
              key={group.shipment.id}
              className="border border-gray-200 rounded-lg overflow-hidden flex flex-col cursor-pointer"
              onClick={() => handleCardClick(group.shipment.id)}
            >
              <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium text-sm">
                      {group.shipment.tracking_code}
                    </span>
                    <span className="mx-2 text-gray-300">|</span>
                    <span className="text-sm text-gray-600">
                      {group.shipment.origin} → {group.shipment.destination}
                    </span>
                  </div>
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded ${
                      group.shipment.status === 'delivered'
                        ? 'bg-green-100 text-green-700'
                        : group.shipment.status === 'in_transit'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-yellow-100 text-yellow-700'
                    }`}
                  >
                    {group.shipment.status}
                  </span>
                </div>
                {group.vendor && (
                  <div className="text-xs text-gray-500 mt-1">
                    Vendor: {group.vendor.name}
                    {group.vendor.country && ` (${group.vendor.country})`}
                  </div>
                )}
                {group.client && (
                  <div className="flex items-center gap-1.5 text-xs text-gray-500 mt-1">
                    <span
                      className="inline-block w-3 h-3 rounded-full"
                      style={{ backgroundColor: group.client.badge_color }}
                    />
                    Client: {group.client.name}
                  </div>
                )}
              </div>

              {isExpanded && (
                <div className="border-t border-gray-200 px-4 py-3 text-sm space-y-3">
                  {detailLoading && !detail ? (
                    <p className="text-gray-400">Loading detail...</p>
                  ) : detail ? (
                    <>
                      <div>
                        <h4 className="font-medium text-gray-700 mb-1">Products</h4>
                        {detail.items.length === 0 ? (
                          <p className="text-gray-400">No products</p>
                        ) : (
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="text-left text-gray-500 border-b">
                                <th className="pb-1">Product</th>
                                <th className="pb-1">Quantity</th>
                                <th className="pb-1">Unit</th>
                              </tr>
                            </thead>
                            <tbody>
                              {detail.items.map((item) => (
                                <tr key={item.product_id} className="border-b border-gray-100">
                                  <td className="py-1">{item.product_name}</td>
                                  <td className="py-1">{item.quantity}</td>
                                  <td className="py-1">{item.product_unit ?? '—'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </div>

                      <div className="text-xs text-gray-600 space-y-0.5">
                        <div><span className="font-medium">Dispatched:</span> {new Date(detail.dispatched_at).toLocaleDateString()}</div>
                        <div><span className="font-medium">Expected:</span> {new Date(detail.expected_arrival_at).toLocaleDateString()}</div>
                        {detail.actual_arrival_at && (
                          <div><span className="font-medium">Arrived:</span> {new Date(detail.actual_arrival_at).toLocaleDateString()}</div>
                        )}
                      </div>

                      {detail.status_reason && (
                        <div className="text-xs">
                          <span className="font-medium text-gray-700">Status reason:</span>{' '}
                          <span className="text-gray-600">{detail.status_reason}</span>
                        </div>
                      )}

                      {detail.notes && (
                        <div className="text-xs">
                          <span className="font-medium text-gray-700">Notes:</span>{' '}
                          <span className="text-gray-600">{detail.notes}</span>
                        </div>
                      )}

                      {detail.events.length > 0 && (
                        <div>
                          <h4 className="font-medium text-gray-700 mb-1">Timeline</h4>
                          <ul className="space-y-1 text-xs">
                            {detail.events.map((event, i) => (
                              <li key={i} className="flex gap-2">
                                <span className="text-gray-400 whitespace-nowrap">{new Date(event.occurred_at).toLocaleDateString()}</span>
                                <span className="font-medium">{event.event_type.replace(/_/g, ' ')}</span>
                                <span className="text-gray-500">— {event.location}</span>
                                {event.details && <span className="text-gray-400 italic">({event.details})</span>}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </>
                  ) : null}
                </div>
              )}

            </div>
          )})}
        </div>
      )}
    </div>
  )
}
