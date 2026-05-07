'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { api, setAccessToken } from '@/lib/api'
import { Hexagon, Eye, EyeOff, Loader2, KeyRound } from 'lucide-react'
import { toast } from 'sonner'

type Step = 'credentials' | 'mfa'

export default function LoginPage() {
  const router = useRouter()
  const [step, setStep] = useState<Step>('credentials')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)
  const [mfaCode, setMfaCode] = useState('')
  const [mfaTicket, setMfaTicket] = useState<string | undefined>(undefined)

  async function handleCredentialsSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!username || !password) return
    setLoading(true)
    try {
      const res = await api.login(username, password)
      if (res.mfa_required) {
        // TODO(backend): align ticket field name; we forward whatever was sent.
        setMfaTicket(res.mfa_ticket)
        setStep('mfa')
        toast.message('Multi-factor authentication required')
        return
      }
      setAccessToken(res.access_token, res.refresh_token)
      router.push('/')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  async function handleMfaSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!/^\d{6}$/.test(mfaCode)) {
      toast.error('Enter the 6-digit code from your authenticator')
      return
    }
    setLoading(true)
    try {
      const res = await api.verifyMfa({
        username,
        code: mfaCode,
        ticket: mfaTicket,
      })
      setAccessToken(res.access_token, res.refresh_token)
      router.push('/')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Invalid MFA code')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Hexagon className="w-10 h-10 text-blue-400" strokeWidth={1.5} />
            <span className="text-3xl font-bold tracking-tight">Atalaya</span>
          </div>
          <p className="text-sm text-gray-500">Open Intelligence Platform</p>
        </div>

        {step === 'credentials' && (
          <form
            onSubmit={handleCredentialsSubmit}
            className="bg-surface border border-border rounded-xl p-6 space-y-4"
            aria-label="Sign in"
          >
            <div>
              <label htmlFor="username" className="text-xs text-gray-400 mb-1.5 block">
                Username
              </label>
              <input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                autoComplete="username"
                placeholder="admin"
                className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
            <div>
              <label htmlFor="password" className="text-xs text-gray-400 mb-1.5 block">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  placeholder="********"
                  className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2.5 text-sm pr-10 focus:outline-none focus:border-blue-500 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPw((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading || !username || !password}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>
        )}

        {step === 'mfa' && (
          <form
            onSubmit={handleMfaSubmit}
            className="bg-surface border border-border rounded-xl p-6 space-y-4"
            aria-label="Multi-factor authentication"
          >
            <div className="flex items-center gap-2 text-blue-400">
              <KeyRound className="w-4 h-4" aria-hidden />
              <h2 className="text-sm font-semibold">Two-factor authentication</h2>
            </div>
            <p className="text-xs text-gray-400">
              Enter the 6-digit code from your authenticator app for{' '}
              <span className="font-mono text-gray-200">{username}</span>.
            </p>
            <div>
              <label htmlFor="mfa-code" className="text-xs text-gray-400 mb-1.5 block">
                Verification code
              </label>
              <input
                id="mfa-code"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ''))}
                autoFocus
                autoComplete="one-time-code"
                placeholder="123456"
                className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2.5 text-lg tracking-widest text-center font-mono focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
            <button
              type="submit"
              disabled={loading || mfaCode.length !== 6}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? 'Verifying…' : 'Verify'}
            </button>
            <button
              type="button"
              onClick={() => {
                setStep('credentials')
                setMfaCode('')
              }}
              className="w-full text-xs text-gray-500 hover:text-gray-300"
            >
              Cancel and use different credentials
            </button>
          </form>
        )}

        <p className="text-center text-xs text-gray-600 mt-6">
          Access restricted to authorized personnel only.
        </p>
      </div>
    </div>
  )
}
