import React, { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Activity, Lock, Mail, AlertCircle, ArrowRight, Loader2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

export default function LoginPage() {
  useDocumentTitle('Project Doctor', 'Sign In')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as any)?.from?.pathname || '/'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)

    const trimmedEmail = email.trim()
    if (!trimmedEmail) {
      setErrorMessage('Please enter your email address.')
      return
    }

    // Basic email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(trimmedEmail)) {
      setErrorMessage('Please enter a valid email address.')
      return
    }

    if (!password) {
      setErrorMessage('Please enter your password.')
      return
    }

    setSubmitting(true)
    try {
      await login({ email: trimmedEmail, password })
      navigate(from, { replace: true })
    } catch (err: any) {
      if (err.response) {
        // HTTP Error responses from FastAPI
        if (err.response.status === 401) {
          setErrorMessage('Invalid email or password. Please verify your credentials.')
        } else if (err.response.status === 400 && err.response.data?.detail) {
          setErrorMessage(err.response.data.detail)
        } else if (err.response.status === 422) {
          setErrorMessage('Validation error: Please check your email format.')
        } else {
          setErrorMessage('An unexpected error occurred during login. Please try again.')
        }
      } else if (err.request) {
        setErrorMessage('Server unavailable. Please ensure the backend server is running.')
      } else {
        setErrorMessage('Failed to submit login request.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans selection:bg-blue-600 selection:text-white">
      {/* Brand Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex items-center justify-center h-12 w-12 rounded-xl bg-blue-600/10 border border-blue-500/30 text-blue-400 mb-4">
          <Activity className="h-6 w-6" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Sign in to Project Doctor</h2>
        <p className="mt-1 text-sm text-slate-400">
          Access your repository diagnostics and software health reports
        </p>
      </div>

      {/* Login Card */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-[#0d1322] py-8 px-6 sm:px-8 border border-slate-800 rounded-xl shadow-xl space-y-6">
          {/* Error Banner */}
          {errorMessage && (
            <div className="rounded-lg bg-rose-950/40 border border-rose-500/30 p-3.5 flex items-start space-x-3 text-rose-300 text-xs">
              <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="leading-relaxed font-medium">{errorMessage}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5" htmlFor="email">
                Email Address
              </label>
              <div className="relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="developer@example.com"
                  autoComplete="email"
                  required
                  className="block w-full pl-9 pr-3 py-2 bg-slate-900/90 border border-slate-800 rounded-lg text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-medium text-slate-300" htmlFor="password">
                  Password
                </label>
              </div>
              <div className="relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  autoComplete="current-password"
                  required
                  className="block w-full pl-9 pr-3 py-2 bg-slate-900/90 border border-slate-800 rounded-lg text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition duration-150 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-[#0d1322]"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-white" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => {
                setEmail('developer@example.com')
                setPassword('password123')
              }}
              className="w-full py-2 px-3 rounded-lg border border-slate-700/80 hover:border-slate-600 bg-slate-800/40 hover:bg-slate-800/80 text-xs text-slate-300 transition duration-150 flex items-center justify-center space-x-1.5"
            >
              <span>Quick Fill Demo:</span>
              <span className="font-mono text-blue-400">developer@example.com</span>
            </button>
          </form>

          {/* Switch to Register */}
          <div className="pt-4 border-t border-slate-800/80 text-center">
            <p className="text-xs text-slate-400">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="font-medium text-blue-400 hover:text-blue-300 transition-colors"
              >
                Create Account
              </Link>
            </p>
          </div>
        </div>

        {/* Security / Quality Note */}
        <p className="mt-6 text-center text-[11px] text-slate-500 font-mono">
          Project Doctor • Passwords hashed with bcrypt (72-byte safe) • JWT session management
        </p>
      </div>
    </div>
  )
}
