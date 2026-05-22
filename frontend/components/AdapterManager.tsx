import React, { useState, useEffect, useRef } from 'react'
import { getApiBaseUrl } from '../lib/api'

export interface AdapterInfo {
  filename: string
  display_name: string
  service_id: string
  description: string
  is_valid: boolean
  warning: string | null
}

interface AdapterManagerProps {
  selectedAdapterId: string
  onSelectAdapter: (id: string) => void
}

export function AdapterManager({ selectedAdapterId, onSelectAdapter }: AdapterManagerProps) {
  const [adapters, setAdapters] = useState<AdapterInfo[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchAdapters = async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/adapters`)
      if (res.ok) {
        const data = await res.json()
        setAdapters(data)
        // Check if current selected is still in valid list, else select the first valid one
        const currentValid = data.find((a: AdapterInfo) => a.service_id === selectedAdapterId && a.is_valid)
        if (!currentValid && data.length > 0) {
          const firstValid = data.find((a: AdapterInfo) => a.is_valid)
          if (firstValid) {
            onSelectAdapter(firstValid.service_id)
          }
        }
      }
    } catch (err) {
      console.error('Failed to fetch adapters:', err)
    }
  }

  useEffect(() => {
    fetchAdapters()
  }, [])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.py')) {
      setUploadError('Only .py adapter files are supported')
      setUploadSuccess(null)
      return
    }

    setUploadError(null)
    setUploadSuccess(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(`${getApiBaseUrl()}/api/adapters/upload`, {
        method: 'POST',
        body: formData,
      })

      if (res.ok) {
        setUploadSuccess(`Adapter "${file.name}" uploaded and registered successfully!`)
        fetchAdapters()
      } else {
        const errText = await res.text()
        const parsed = JSON.parse(errText || '{}')
        setUploadError(parsed.detail || 'Failed to upload and validate adapter')
      }
    } catch (err: any) {
      setUploadError(err.message || 'Failed to upload adapter')
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDelete = async (serviceId: string) => {
    if (['bilibili', 'youtube'].includes(serviceId)) {
      alert('System base adapters (Bilibili/YouTube) cannot be deleted.')
      return
    }

    if (!confirm(`Are you sure you want to delete adapter "${serviceId}"?`)) {
      return
    }

    try {
      const res = await fetch(`${getApiBaseUrl()}/api/adapters/${serviceId}`, {
        method: 'DELETE',
      })

      if (res.ok) {
        fetchAdapters()
      } else {
        const errText = await res.text()
        alert(`Failed to delete adapter: ${errText}`)
      }
    } catch (err: any) {
      alert(`Error deleting adapter: ${err.message}`)
    }
  }

  return (
    <div className="mt-6 border border-slate-700/60 bg-[#0a0a0f] p-4 font-mono">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between text-xs tracking-widest text-cyan-400 hover:text-cyan-300"
      >
        <span>[ADAPTER PLUGINS / 适配器插件管理]</span>
        <span>{isOpen ? '[-]' : '[+]'}</span>
      </button>

      {isOpen && (
        <div className="mt-4 border-t border-slate-800 pt-4">
          <div className="space-y-4">
            {adapters.map((adapter) => {
              const isSelected = selectedAdapterId === adapter.service_id
              const isBase = ['bilibili', 'youtube'].includes(adapter.service_id)

              return (
                <div
                  key={adapter.service_id}
                  className={`border p-3 ${
                    isSelected ? 'border-cyan-500 bg-cyan-950/5' : 'border-slate-800'
                  } ${!adapter.is_valid ? 'opacity-60 bg-red-950/5' : ''}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <input
                        type="radio"
                        id={`adapter-radio-${adapter.service_id}`}
                        name="adapter-selector"
                        checked={isSelected}
                        disabled={!adapter.is_valid}
                        onChange={() => onSelectAdapter(adapter.service_id)}
                        className="accent-cyan-500 disabled:opacity-30 cursor-pointer"
                      />
                      <label
                        htmlFor={`adapter-radio-${adapter.service_id}`}
                        className={`text-sm font-semibold tracking-wide cursor-pointer ${
                          !adapter.is_valid ? 'text-neutral-500 line-through' : isSelected ? 'text-cyan-400 font-bold' : 'text-cyan-100 hover:text-cyan-300'
                        }`}
                      >
                        {adapter.display_name} ({adapter.filename})
                      </label>
                    </div>

                    {!isBase && (
                      <button
                        type="button"
                        onClick={() => handleDelete(adapter.service_id)}
                        className="text-xs text-red-500 hover:text-red-400 border border-red-500/20 px-2 py-0.5 bg-transparent hover:bg-red-500/5 transition-all"
                      >
                        DELETE
                      </button>
                    )}
                  </div>

                  <p className="mt-1 text-xs text-slate-400 pl-5">{adapter.description || 'No description provided.'}</p>

                  {!adapter.is_valid && (
                    <div className="mt-2 text-xs text-red-400 bg-red-950/20 border border-red-950/40 p-2 pl-5 font-semibold">
                      [!] WARNING: {adapter.warning}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          <div className="mt-6 border-t border-slate-800 pt-4">
            <span className="text-xs text-slate-500 block mb-2 font-semibold">UPLOAD CUSTOM ADAPTER (.py)</span>
            <label className="inline-block cursor-pointer border border-dashed border-cyan-500/40 hover:border-cyan-500 px-4 py-2 text-xs tracking-wider text-cyan-400 hover:bg-cyan-500/5 transition-all">
              <span>UPLOAD PLUGIN FILE</span>
              <input
                ref={fileInputRef}
                type="file"
                accept=".py"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>

            {uploadError && (
              <p className="mt-2 text-xs text-red-400 font-semibold">&gt; Error: {uploadError}</p>
            )}
            {uploadSuccess && (
              <p className="mt-2 text-xs text-fuchsia-400 font-semibold">&gt; {uploadSuccess}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
