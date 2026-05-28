import React, { useState } from 'react'

interface LoginProps {
  onLoginSuccess: () => void
  backendBaseUrl: string
  setBackendBaseUrl: (val: string) => void
}

export default function Login({ onLoginSuccess, backendBaseUrl, setBackendBaseUrl }: LoginProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const normalizedUrl = backendBaseUrl.trim().replace(/\/$/, '')
      
      window.localStorage.setItem('backend-base-url', JSON.stringify(normalizedUrl))

      const res = await fetch(`${normalizedUrl}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })

      if (res.ok) {
        const data = await res.json()
        if (data.success && data.token) {
          window.localStorage.setItem('milano-auth-token', data.token)
          onLoginSuccess()
        } else {
          setError('LOGIN FAILED: Missing token response.')
        }
      } else {
        const errData = await res.json().catch(() => ({}))
        setError(errData.detail || 'INVALID USERNAME OR PASSWORD')
      }
    } catch (e: any) {
      console.error(e)
      setError(`CONNECTION FAILED: Check backend URL or status. (${e.message})`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-md w-full border border-slate-800 bg-[#0a0a0f] p-8 mt-12">
      <h2 className="text-center font-mono text-xl font-bold tracking-widest text-cyan-400 mb-2">// SECURE LOGIN //</h2>
      <p className="text-center font-mono text-[10px] text-fuchsia-400 uppercase tracking-widest mb-8">
        Enter Credentials & Backend URL
      </p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block font-mono text-[10px] font-bold text-cyan-400 uppercase tracking-widest mb-1.5">
            // BACKEND SERVER URL (数据源)
          </label>
          <input
            type="text"
            required
            value={backendBaseUrl}
            onChange={(e) => setBackendBaseUrl(e.target.value)}
            placeholder="http://localhost:8000"
            className="w-full border border-slate-800 bg-slate-950/60 px-3 py-2 font-mono text-xs text-cyan-200 outline-none focus:border-cyan-500 select-all"
          />
        </div>

        <div>
          <label className="block font-mono text-[10px] font-bold text-cyan-400 uppercase tracking-widest mb-1.5">
            // USERNAME (用户名)
          </label>
          <input
            type="text"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username"
            className="w-full border border-slate-800 bg-slate-950/60 px-3 py-2 font-mono text-xs text-cyan-200 outline-none focus:border-cyan-500"
          />
        </div>

        <div>
          <label className="block font-mono text-[10px] font-bold text-cyan-400 uppercase tracking-widest mb-1.5">
            // PASSWORD (密码)
          </label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="w-full border border-slate-800 bg-slate-950/60 px-3 py-2 font-mono text-xs text-cyan-200 outline-none focus:border-cyan-500"
          />
        </div>

        {error && (
          <div className="border border-red-500/50 bg-red-950/20 px-3 py-2 font-mono text-[11px] text-red-400 uppercase text-center">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full border border-cyan-500 bg-cyan-950/10 hover:bg-cyan-500/20 disabled:opacity-40 py-2.5 font-mono text-xs text-cyan-400 uppercase tracking-widest font-bold transition-all"
        >
          {loading ? 'AUTHENTICATING...' : '[ ENTER LIBRARY ]'}
        </button>
      </form>
    </div>
  )
}
