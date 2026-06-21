import apiClient from './client'

export interface ProductRead {
  id: string
  category_id: string | null
  name: string
  description: string | null
  quantity: number
  unit: string | null
  added_by: string | null
  created_at: string
}

export interface ProductCreate {
  category_id?: string | null
  name: string
  description?: string | null
  quantity?: number
  unit?: string | null
}

export interface ProductUpdate {
  name?: string | null
  description?: string | null
  quantity?: number | null
  unit?: string | null
  category_id?: string | null
}

export interface ShipmentRead {
  id: string
  tracking_code: string
  vendor_id: string
  purchase_order_id: string | null
  client_id: string | null
  origin: string
  destination: string
  status: string
  dispatched_at: string
  expected_arrival_at: string
  actual_arrival_at: string | null
  delay_reason: string | null
  notes: string | null
  created_at: string
}

export async function listProducts(): Promise<ProductRead[]> {
  const response = await apiClient.get<ProductRead[]>('/api/v1/products')
  return response.data
}

export async function getProduct(id: string): Promise<ProductRead> {
  const response = await apiClient.get<ProductRead>(`/api/v1/products/${id}`)
  return response.data
}

export async function createProduct(data: ProductCreate): Promise<ProductRead> {
  const response = await apiClient.post<ProductRead>('/api/v1/products', data)
  return response.data
}

export async function updateProduct(id: string, data: ProductUpdate): Promise<ProductRead> {
  const response = await apiClient.put<ProductRead>(`/api/v1/products/${id}`, data)
  return response.data
}

export async function deleteProduct(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/products/${id}`)
}

export interface VendorRead {
  id: string
  name: string
  contact: string | null
  email: string | null
  country: string | null
  created_at: string
}

export async function listShipments(): Promise<ShipmentRead[]> {
  const response = await apiClient.get<ShipmentRead[]>('/api/v1/shipments')
  return response.data
}

export interface VendorCreate {
  name: string
  contact?: string | null
  email?: string | null
  country?: string | null
}

export interface VendorUpdate {
  name?: string | null
  contact?: string | null
  email?: string | null
  country?: string | null
}

export async function listVendors(): Promise<VendorRead[]> {
  const response = await apiClient.get<VendorRead[]>('/api/v1/vendors')
  return response.data
}

export async function getVendor(id: string): Promise<VendorRead> {
  const response = await apiClient.get<VendorRead>(`/api/v1/vendors/${id}`)
  return response.data
}

export async function createVendor(data: VendorCreate): Promise<VendorRead> {
  const response = await apiClient.post<VendorRead>('/api/v1/vendors', data)
  return response.data
}

export async function updateVendor(id: string, data: VendorUpdate): Promise<VendorRead> {
  const response = await apiClient.put<VendorRead>(`/api/v1/vendors/${id}`, data)
  return response.data
}

export async function deleteVendor(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/vendors/${id}`)
}

export interface ClientRead {
  id: string
  name: string
  contact: string | null
  email: string | null
  country: string | null
  badge_color: string
  created_at: string
}

export interface ClientCreate {
  name: string
  contact?: string | null
  email?: string | null
  country?: string | null
  badge_color?: string
}

export interface ClientUpdate {
  name?: string | null
  contact?: string | null
  email?: string | null
  country?: string | null
  badge_color?: string | null
}

export async function listClients(): Promise<ClientRead[]> {
  const response = await apiClient.get<ClientRead[]>('/api/v1/clients')
  return response.data
}

export async function getClient(id: string): Promise<ClientRead> {
  const response = await apiClient.get<ClientRead>(`/api/v1/clients/${id}`)
  return response.data
}

export async function createClient(data: ClientCreate): Promise<ClientRead> {
  const response = await apiClient.post<ClientRead>('/api/v1/clients', data)
  return response.data
}

export async function updateClient(id: string, data: ClientUpdate): Promise<ClientRead> {
  const response = await apiClient.put<ClientRead>(`/api/v1/clients/${id}`, data)
  return response.data
}

export async function deleteClient(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/clients/${id}`)
}
