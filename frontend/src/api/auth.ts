import apiClient from './client'

export interface TokenResponse {
  access_token: string
  token_type: string
}

export async function loginApi(email: string, password: string): Promise<TokenResponse> {
  const response = await apiClient.post<TokenResponse>('/auth/login', { email, password })
  return response.data
}
