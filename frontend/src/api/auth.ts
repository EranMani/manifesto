import apiClient from './client'

export interface TokenResponse {
  access_token: string
  token_type: string
}

export async function loginApi(email: string, password: string): Promise<TokenResponse> {
  const body = new URLSearchParams()
  body.append('username', email)
  body.append('password', password)

  const response = await apiClient.post<TokenResponse>('/auth/login', body, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  })

  return response.data
}
