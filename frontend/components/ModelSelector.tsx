import React from 'react'
import type { LocalModel } from '~/lib/types'
import type { ModelType, ModelStatus } from '~/hooks/useModelManager'

interface ModelSelectorProps {
  modelType: ModelType
  selectedLocalModel: string
  models: LocalModel[]
  statusMap: Record<string, ModelStatus>
  onModelTypeChange: (type: ModelType) => void
  onLocalModelChange: (name: string) => void
  onDownload: (name: string) => void
}

export function ModelSelector({
  modelType,
  selectedLocalModel,
  models,
  statusMap,
  onModelTypeChange,
  onLocalModelChange,
  onDownload,
}: ModelSelectorProps) {
  return (
    <div className="mt-6 border border-slate-700 bg-slate-900/30 p-4">
      <h3 className="mb-3 font-mono text-xs tracking-wider text-slate-400">MODEL SOURCE</h3>

      <div className="flex gap-6">
        <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-slate-300">
          <input
            type="radio"
            name="modelType"
            value="online"
            checked={modelType === 'online'}
            onChange={() => onModelTypeChange('online')}
            className="accent-cyan-500"
          />
          在线服务 (OpenAI)
        </label>
        <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-slate-300">
          <input
            type="radio"
            name="modelType"
            value="local"
            checked={modelType === 'local'}
            onChange={() => onModelTypeChange('local')}
            className="accent-cyan-500"
          />
          本地模型 (Whisper)
        </label>
      </div>

      {modelType === 'local' && (
        <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {models.map((m) => {
            const status = statusMap[m.name] || {
              status: m.installed ? 'installed' : 'not_installed',
              progress: m.installed ? 100 : 0,
              error: null,
            }
            const isInstalled = status.status === 'installed' || status.status === 'completed'
            const isDownloading = status.status === 'downloading'
            const isSelected = selectedLocalModel === m.name

            return (
              <div
                key={m.name}
                className={`relative border p-3 transition-colors ${
                  isSelected && isInstalled
                    ? 'border-cyan-500 bg-cyan-950/20'
                    : 'border-slate-700 bg-slate-900/20'
                } ${!isInstalled ? 'opacity-60' : ''}`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-cyan-100">{m.label}</span>
                  <span className="font-mono text-[10px] text-slate-500">{m.size}</span>
                </div>

                {isInstalled ? (
                  <button
                    type="button"
                    onClick={() => onLocalModelChange(m.name)}
                    className={`mt-2 w-full border py-1 font-mono text-[10px] tracking-wider transition-colors ${
                      isSelected
                        ? 'border-cyan-500 bg-cyan-950/30 text-cyan-400'
                        : 'border-slate-600 text-slate-400 hover:border-cyan-500 hover:text-cyan-400'
                    }`}
                  >
                    {isSelected ? 'SELECTED' : 'SELECT'}
                  </button>
                ) : isDownloading ? (
                  <div className="mt-2">
                    <div className="h-1 w-full bg-slate-700">
                      <div
                        className="h-1 bg-cyan-500 transition-all"
                        style={{ width: `${status.progress}%` }}
                      />
                    </div>
                    <p className="mt-1 font-mono text-[10px] text-cyan-400">
                      DOWNLOADING {status.progress}%
                    </p>
                    <p className="mt-0.5 font-mono text-[9px] text-slate-500">
                      大模型下载较慢，请耐心等待...
                    </p>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => onDownload(m.name)}
                    className="mt-2 w-full border border-fuchsia-500/40 py-1 font-mono text-[10px] tracking-wider text-fuchsia-400 transition-colors hover:border-fuchsia-500 hover:bg-fuchsia-950/20"
                  >
                    INSTALL
                  </button>
                )}

                {status.error && (
                  <p className="mt-1 font-mono text-[10px] text-red-400">{status.error}</p>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
