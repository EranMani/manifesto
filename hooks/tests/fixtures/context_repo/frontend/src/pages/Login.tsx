import { loginApi } from "../api/auth"

export async function submitLogin(email: string, password: string) {
  return loginApi(email, password)
}
