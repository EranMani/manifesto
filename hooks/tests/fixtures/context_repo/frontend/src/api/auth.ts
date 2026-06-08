import { apiClient } from "./client"

export async function login(email: string, password: string) {
  return apiClient.post("/auth/login", { email, password })
}
