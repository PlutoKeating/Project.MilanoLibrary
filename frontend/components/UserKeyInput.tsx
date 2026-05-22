import React from 'react'

type UserKeyInputProps = {
  value: string | undefined
  onChange: (e: any) => void
  baseUrl: string | undefined
  onBaseUrlChange: (e: any) => void
  modelName: string | undefined
  onModelNameChange: (e: any) => void
  backendBaseUrl?: string | undefined
  onBackendBaseUrlChange?: (e: any) => void
}

export function UserKeyInput(props: UserKeyInputProps) {
  return (
    <details className="mt-8">
      <summary className="cursor-pointer font-mono text-xs tracking-wider text-cyan-500 hover:text-cyan-400">
        [+] API CONFIGURATION
      </summary>
      <div className="mt-3 space-y-2">
        <input
          value={props.value || ''}
          onChange={props.onChange}
          className="w-full border border-slate-700 bg-slate-900/50 px-3 py-2 font-mono text-xs text-cyan-100 placeholder-slate-600 outline-none focus:border-cyan-500"
          placeholder="API KEY"
        />
        <input
          value={props.baseUrl || ''}
          onChange={props.onBaseUrlChange}
          className="w-full border border-slate-700 bg-slate-900/50 px-3 py-2 font-mono text-xs text-cyan-100 placeholder-slate-600 outline-none focus:border-cyan-500"
          placeholder="OPENAI BASE URL (optional)"
        />
        <input
          value={props.backendBaseUrl || ''}
          onChange={props.onBackendBaseUrlChange}
          className="w-full border border-slate-700 bg-slate-900/50 px-3 py-2 font-mono text-xs text-cyan-100 placeholder-slate-600 outline-none focus:border-cyan-500"
          placeholder="BACKEND URL (default: http://localhost:8000)"
        />
        <input
          value={props.modelName || ''}
          onChange={props.onModelNameChange}
          className="w-full border border-slate-700 bg-slate-900/50 px-3 py-2 font-mono text-xs text-cyan-100 placeholder-slate-600 outline-none focus:border-cyan-500"
          placeholder="MODEL NAME (optional)"
        />
      </div>
    </details>
  )
}
