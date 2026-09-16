import { api } from './api'
import type { LoginPayload, RegisterPayload, TokenResponse, User } from '../types/auth'

export const authService = {
  async register(payload: RegisterPayload): Promise<User> {
    const response = await api.post<User>('/auth/register', payload)
    return response.data
  },

  async login(payload: LoginPayload): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/login', payload)
    return response.data
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me')
    return response.data
  },

  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout')
    } catch {
      // Even if network call fails, we still proceed to clear local state
    }
  },
}
