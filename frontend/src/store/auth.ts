import { create } from 'zustand'

interface User {
  id: string
  role: string
  name: string
}

interface AuthState {
  token: string | null
  user: User | null
  login: (token: string, user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  login: (token: string, user: User) => set({ token, user }),
  logout: () => set({ token: null, user: null }),
}))
