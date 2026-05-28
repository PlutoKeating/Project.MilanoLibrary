import React, { useState, useEffect } from 'react'
import { FileExplorer } from './FileExplorer'
import { getApiBaseUrl } from '~/lib/api'

interface SettingsTabProps {
  vaultPath: string
  handleSaveVault: (path: string) => Promise<void>
  vaultMessage: string
  userKey: string
  setUserKey: (val: string) => void
  userBaseUrl: string
  setUserBaseUrl: (val: string) => void
  userModelName: string
  setUserModelName: (val: string) => void
  backendBaseUrl: string
  setBackendBaseUrl: (val: string) => void
}

export default function SettingsTab({
  vaultPath,
  handleSaveVault,
  vaultMessage,
  userKey,
  setUserKey,
  userBaseUrl,
  setUserBaseUrl,
  userModelName,
  setUserModelName,
  backendBaseUrl,
  setBackendBaseUrl
}: SettingsTabProps) {
  const [showExplorer, setShowExplorer] = useState(false)

  // API Config local temporary states
  const [localUserKey, setLocalUserKey] = useState(userKey || '')
  const [localUserBaseUrl, setLocalUserBaseUrl] = useState(userBaseUrl || '')
  const [localUserModelName, setLocalUserModelName] = useState(userModelName || '')
  const [localBackendBaseUrl, setLocalBackendBaseUrl] = useState(backendBaseUrl || '')
  const [apiConfigMessage, setApiConfigMessage] = useState('')
  const [isVerifying, setIsVerifying] = useState(false)
  const [verificationError, setVerificationError] = useState('')
  const [verificationSuccess, setVerificationSuccess] = useState('')

  // CRUD User accounts states
  const [users, setUsers] = useState<{ uuid: string; username: string; password: string }[]>([])
  const [newUsername, setNewUsername] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [editingUuid, setEditingUuid] = useState<string | null>(null)
  const [editingUsername, setEditingUsername] = useState('')
  const [editingPassword, setEditingPassword] = useState('')
  const [accountsError, setAccountsError] = useState('')
  const [accountsMessage, setAccountsMessage] = useState('')
  const [showPasswords, setShowPasswords] = useState<{ [uuid: string]: boolean }>({})

  // Sync state from props on changes
  useEffect(() => {
    setLocalUserKey(userKey || '')
  }, [userKey])

  useEffect(() => {
    setLocalUserBaseUrl(userBaseUrl || '')
  }, [userBaseUrl])

  useEffect(() => {
    setLocalUserModelName(userModelName || '')
  }, [userModelName])

  useEffect(() => {
    setLocalBackendBaseUrl(backendBaseUrl || '')
  }, [backendBaseUrl])

  const handleSaveApiConfig = () => {
    setUserKey(localUserKey)
    setUserBaseUrl(localUserBaseUrl)
    setUserModelName(localUserModelName)
    setBackendBaseUrl(localBackendBaseUrl)

    // Save normalized base URL directly to raw local storage for immediate hook updates
    const normalizedUrl = localBackendBaseUrl.trim().replace(/\/$/, '')
    window.localStorage.setItem('backend-base-url', JSON.stringify(normalizedUrl))

    setApiConfigMessage('API CONFIGURATION SAVED SUCCESSFULLY!')
    setTimeout(() => setApiConfigMessage(''), 3000)
  }

  const handleVerifyConnectivity = async () => {
    setIsVerifying(true)
    setVerificationError('')
    setVerificationSuccess('')

    const keyToTest = localUserKey.trim()
    const baseUrlToTest = localUserBaseUrl.trim()
    const modelToTest = localUserModelName.trim()
    const backendUrlToTest = localBackendBaseUrl.trim().replace(/\/$/, '') || getApiBaseUrl()

    try {
      const res = await fetch(`${backendUrlToTest}/api/models/verify-connectivity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_key: keyToTest || null,
          base_url: baseUrlToTest || null,
          model_name: modelToTest || null
        })
      })

      if (res.ok) {
        const data = await res.json()
        setVerificationSuccess(data.message || 'CONNECTIVITY VERIFIED SUCCESSFULLY!')
      } else {
        const data = await res.json().catch(() => ({}))
        setVerificationError(data.detail || 'Failed to verify connectivity.')
      }
    } catch (err: any) {
      setVerificationError(`NETWORK ERROR: ${err.message || 'Cannot reach backend server.'} Please verify your BACKEND URL and network.`)
    } finally {
      setIsVerifying(false)
    }
  }

  const fetchUsers = async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/auth/users`)
      if (res.ok) {
        const data = await res.json()
        setUsers(data)
      }
    } catch (e) {
      console.error('Error fetching users:', e)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault()
    setAccountsError('')
    setAccountsMessage('')
    const u = newUsername.trim()
    const p = newPassword.trim()
    if (!u || !p) {
      setAccountsError('Username and password cannot be empty')
      return
    }

    try {
      const res = await fetch(`${getApiBaseUrl()}/api/auth/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p })
      })

      if (res.ok) {
        setAccountsMessage(`User "${u}" added successfully!`)
        setNewUsername('')
        setNewPassword('')
        fetchUsers()
      } else {
        const data = await res.json().catch(() => ({}))
        setAccountsError(data.detail || 'Failed to add user')
      }
    } catch (err: any) {
      setAccountsError(`Error: ${err.message}`)
    }
  }

  const handleUpdateUser = async (uuid: string) => {
    setAccountsError('')
    setAccountsMessage('')
    const u = editingUsername.trim()
    const p = editingPassword.trim()
    if (!u || !p) {
      setAccountsError('Username and password cannot be empty')
      return
    }

    try {
      const res = await fetch(`${getApiBaseUrl()}/api/auth/users/${uuid}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p })
      })

      if (res.ok) {
        setAccountsMessage(`User account updated successfully!`)
        setEditingUuid(null)
        setEditingUsername('')
        setEditingPassword('')
        fetchUsers()
      } else {
        const data = await res.json().catch(() => ({}))
        setAccountsError(data.detail || 'Failed to update user')
      }
    } catch (err: any) {
      setAccountsError(`Error: ${err.message}`)
    }
  }

  const handleDeleteUser = async (uuid: string, username: string) => {
    if (!confirm(`CONFIRM DELETION OF USER ACCOUNT "${username}"?`)) return
    setAccountsError('')
    setAccountsMessage('')

    try {
      const res = await fetch(`${getApiBaseUrl()}/api/auth/users/${uuid}`, {
        method: 'DELETE'
      })

      if (res.ok) {
        setAccountsMessage(`User "${username}" deleted successfully!`)
        fetchUsers()
      } else {
        const data = await res.json().catch(() => ({}))
        setAccountsError(data.detail || 'Failed to delete user')
      }
    } catch (err: any) {
      setAccountsError(`Error: ${err.message}`)
    }
  }

  const toggleShowPassword = (uuid: string) => {
    setShowPasswords(prev => ({ ...prev, [uuid]: !prev[uuid] }))
  }

  return (
    <div className="mt-8 space-y-6 max-w-4xl mx-auto">
      <h3 className="font-mono text-xs font-bold text-fuchsia-400 uppercase tracking-widest">// SETTINGS / 系统配置</h3>
      
      {/* Obsidian Root Vault Path */}
      <div className="border border-slate-800 bg-[#0a0a0f] p-6">
        <label className="block font-mono text-xs font-bold text-cyan-400 uppercase tracking-widest mb-2">
          // OBSIDIAN ROOT VAULT PATH (本地书籍根目录)
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            readOnly
            placeholder="选择磁盘上的书籍根目录绝对路径..."
            value={vaultPath}
            className="flex-1 border border-slate-800 bg-slate-950/60 px-3 py-2 font-mono text-xs text-cyan-200 outline-none select-all cursor-not-allowed"
          />
          <button
            type="button"
            onClick={() => setShowExplorer(!showExplorer)}
            className="border border-slate-700 hover:border-cyan-500 hover:bg-cyan-500/10 px-4 py-2 font-mono text-xs text-cyan-400 uppercase font-bold transition-colors"
          >
            {showExplorer ? 'HIDE BROWSE' : 'BROWSE...'}
          </button>
        </div>

        {showExplorer && (
          <div className="mt-4">
            <FileExplorer
              backendUrl={getApiBaseUrl()}
              initialPath={vaultPath}
              onSelect={(selectedPath) => {
                handleSaveVault(selectedPath)
                setShowExplorer(false)
              }}
              onClose={() => setShowExplorer(false)}
            />
          </div>
        )}

        {vaultMessage && (
          <p className="mt-2 font-mono text-[10px] text-cyan-400 uppercase tracking-wider font-bold">
            {vaultMessage}
          </p>
        )}
      </div>

      {/* Accounts Manager Card */}
      <div className="border border-slate-800 bg-[#0a0a0f] p-6">
        <label className="block font-mono text-xs font-bold text-cyan-400 uppercase tracking-widest mb-4">
          // ACCOUNTS MANAGER / 用户账户管理 (CRUD // UUID 定位)
        </label>

        {/* User accounts list */}
        <div className="space-y-4 mb-6">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse border border-slate-800 text-left font-mono text-xs">
              <thead>
                <tr className="bg-slate-900/30 text-cyan-400">
                  <th className="border border-slate-800 p-2.5">UUID</th>
                  <th className="border border-slate-800 p-2.5">USERNAME</th>
                  <th className="border border-slate-800 p-2.5">PASSWORD</th>
                  <th className="border border-slate-800 p-2.5 text-center">ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.uuid} className="hover:bg-slate-900/10">
                    <td className="border border-slate-800 p-2.5 text-slate-500 text-[9px] font-bold select-all">{u.uuid}</td>
                    <td className="border border-slate-800 p-2.5 text-cyan-200 font-bold">
                      {editingUuid === u.uuid ? (
                        <input
                          type="text"
                          value={editingUsername}
                          onChange={(e) => setEditingUsername(e.target.value)}
                          className="border border-slate-700 bg-slate-950 px-2 py-1 font-mono text-xs text-cyan-100 outline-none w-full font-bold"
                          placeholder="Username"
                        />
                      ) : (
                        u.username
                      )}
                    </td>
                    <td className="border border-slate-800 p-2.5">
                      {editingUuid === u.uuid ? (
                        <input
                          type="text"
                          value={editingPassword}
                          onChange={(e) => setEditingPassword(e.target.value)}
                          className="border border-slate-700 bg-slate-950 px-2 py-1 font-mono text-xs text-cyan-100 outline-none w-full"
                          placeholder="Password"
                        />
                      ) : (
                        <span className="font-mono">
                          {showPasswords[u.uuid] ? u.password : '••••••••'}
                        </span>
                      )}
                    </td>
                    <td className="border border-slate-800 p-2.5 text-center space-x-2 whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => toggleShowPassword(u.uuid)}
                        className="text-[10px] text-fuchsia-400 hover:text-fuchsia-300 font-bold"
                      >
                        [{showPasswords[u.uuid] ? 'HIDE' : 'SHOW'}]
                      </button>

                      {editingUuid === u.uuid ? (
                        <>
                          <button
                            type="button"
                            onClick={() => handleUpdateUser(u.uuid)}
                            className="text-[10px] text-green-400 hover:text-green-300 font-bold"
                          >
                            [SAVE]
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setEditingUuid(null)
                              setEditingUsername('')
                              setEditingPassword('')
                            }}
                            className="text-[10px] text-slate-500 hover:text-slate-400 font-bold"
                          >
                            [CANCEL]
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => {
                              setEditingUuid(u.uuid)
                              setEditingUsername(u.username)
                              setEditingPassword(u.password)
                            }}
                            className="text-[10px] text-cyan-400 hover:text-cyan-300 font-bold"
                          >
                            [EDIT]
                          </button>
                          <button
                            type="button"
                            disabled={users.length <= 1}
                            onClick={() => handleDeleteUser(u.uuid, u.username)}
                            className="text-[10px] text-red-500 hover:text-red-400 font-bold disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            [DELETE]
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Add user form */}
        <form onSubmit={handleAddUser} className="border-t border-slate-900 pt-4 space-y-4">
          <p className="font-mono text-[10px] text-slate-500">// REGISTER NEW CREDENTIAL PAIR / 注册新账户对</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <input
              type="text"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              className="border border-slate-700 bg-slate-900/50 px-3 py-2 font-mono text-xs text-cyan-100 placeholder-slate-600 outline-none focus:border-cyan-500"
              placeholder="NEW USERNAME"
            />
            <input
              type="text"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="border border-slate-700 bg-slate-900/50 px-3 py-2 font-mono text-xs text-cyan-100 placeholder-slate-600 outline-none focus:border-cyan-500"
              placeholder="NEW PASSWORD"
            />
          </div>
          <button
            type="submit"
            className="border border-cyan-500 hover:bg-cyan-500/10 px-4 py-2 font-mono text-xs text-cyan-400 uppercase font-bold transition-colors w-full"
          >
            [ ADD USER ACCOUNT / 添加该账户对 ]
          </button>
        </form>

        {accountsError && (
          <p className="mt-3 font-mono text-[11px] text-red-400 font-bold uppercase">{accountsError}</p>
        )}
        {accountsMessage && (
          <p className="mt-3 font-mono text-[11px] text-cyan-400 font-bold uppercase">{accountsMessage}</p>
        )}
      </div>

      {/* Global Key Config */}
      <div className="border border-slate-800 bg-[#0a0a0f] p-6">
        <label className="block font-mono text-xs font-bold text-cyan-400 uppercase tracking-widest mb-4">
          // API CONFIGURATION / API参数设置
        </label>
        <div className="space-y-4">
          <div>
            <label className="block font-mono text-[10px] text-slate-500 mb-1">OPENAI API KEY</label>
            <input
              value={localUserKey}
              onChange={(e) => setLocalUserKey(e.target.value)}
              className="w-full border border-slate-700 bg-slate-900/50 px-3 py-2 font-mono text-xs text-cyan-100 placeholder-slate-600 outline-none focus:border-cyan-500"
              placeholder="API KEY"
            />
          </div>
          <div>
            <label className="block font-mono text-[10px] text-slate-500 mb-1">OPENAI BASE URL (optional)</label>
            <input
              value={localUserBaseUrl}
              onChange={(e) => setLocalUserBaseUrl(e.target.value)}
              className="w-full border border-slate-700 bg-slate-900/50 px-3 py-2 font-mono text-xs text-cyan-100 placeholder-slate-600 outline-none focus:border-cyan-500"
              placeholder="OPENAI BASE URL (optional)"
            />
          </div>
          <div>
            <label className="block font-mono text-[10px] text-slate-500 mb-1">BACKEND URL</label>
            <input
              value={localBackendBaseUrl}
              onChange={(e) => setLocalBackendBaseUrl(e.target.value)}
              className="w-full border border-slate-700 bg-slate-900/50 px-3 py-2 font-mono text-xs text-cyan-100 placeholder-slate-600 outline-none focus:border-cyan-500"
              placeholder="BACKEND URL (default: http://localhost:8000)"
            />
          </div>
          <div>
            <label className="block font-mono text-[10px] text-slate-500 mb-1">MODEL NAME (optional)</label>
            <input
              value={localUserModelName}
              onChange={(e) => setLocalUserModelName(e.target.value)}
              className="w-full border border-slate-700 bg-slate-900/50 px-3 py-2 font-mono text-xs text-cyan-100 placeholder-slate-600 outline-none focus:border-cyan-500"
              placeholder="MODEL NAME (optional)"
            />
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <button
              type="button"
              onClick={handleSaveApiConfig}
              className="border border-cyan-500 hover:bg-cyan-500/10 px-4 py-2 font-mono text-xs text-cyan-400 uppercase font-bold transition-colors w-full"
            >
              [ SAVE API CONFIGURATION / 保存API参数 ]
            </button>
            <button
              type="button"
              disabled={isVerifying}
              onClick={handleVerifyConnectivity}
              className="border border-fuchsia-500 hover:bg-fuchsia-500/10 disabled:opacity-50 px-4 py-2 font-mono text-xs text-fuchsia-400 uppercase font-bold transition-colors w-full"
            >
              {isVerifying ? '[ VERIFYING CONNECTIVITY... / 正在验证... ]' : '[ VERIFY CONNECTIVITY / 验证连通性 ]'}
            </button>
          </div>
        </div>

        {apiConfigMessage && (
          <p className="mt-3 font-mono text-[11px] text-cyan-400 font-bold uppercase">{apiConfigMessage}</p>
        )}

        {verificationSuccess && (
          <p className="mt-3 font-mono text-[11px] text-cyan-400 font-bold uppercase">{verificationSuccess}</p>
        )}

        {verificationError && (
          <p className="mt-3 font-mono text-[11px] text-red-400 font-bold uppercase">{verificationError}</p>
        )}
      </div>
    </div>
  )
}
