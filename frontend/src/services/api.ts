import axios from 'axios'

let rawBase = import.meta.env.VITE_API_URL || '/api'
if (typeof rawBase === 'string') {
  rawBase = rawBase.trim()
  if (rawBase.endsWith('/')) {
    rawBase = rawBase.slice(0, -1)
  }
  if (rawBase.startsWith('http') && !rawBase.endsWith('/api')) {
    rawBase = `${rawBase}/api`
  }
}
const API_BASE_URL = rawBase || '/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor to handle auth expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear token if expired/invalid
      const currentPath = window.location.pathname
      if (currentPath !== '/login' && currentPath !== '/register' && currentPath !== '/') {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
      }
    }
    return Promise.reject(error)
  }
)

export interface HealthCheckResponse {
  status: string
  database: string
  environment: string
  version: string
  timestamp: string
}

export const checkHealth = async (): Promise<HealthCheckResponse> => {
  const res = await api.get<HealthCheckResponse>('/health')
  return res.data
}
