import React, { useEffect, useState } from 'react'

interface FileExplorerProps {
  backendUrl: string
  initialPath?: string
  onSelect: (path: string) => void
  onClose: () => void
}

export function FileExplorer({ backendUrl, initialPath, onSelect, onClose }: FileExplorerProps) {
  const [currentPath, setCurrentPath] = useState(initialPath || '')
  const [parentPath, setParentPath] = useState<string | null>(null)
  const [subdirs, setSubdirs] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fetchDirectory = async (path: string) => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${backendUrl}/api/books/settings/browse?path=${encodeURIComponent(path)}`)
      if (res.ok) {
        const data = await res.json()
        setCurrentPath(data.current_path)
        setParentPath(data.parent_path)
        setSubdirs(data.subdirs || [])
      } else {
        const err = await res.json()
        setError(err.detail || 'Failed to load directory')
      }
    } catch (err) {
      setError('Connection to backend failed')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDirectory(initialPath || '')
  }, [initialPath])

  const handleSelectSubdir = (dir: string) => {
    const nextPath = currentPath ? `${currentPath}/${dir}` : dir
    fetchDirectory(nextPath)
  }

  const handleGoParent = () => {
    if (parentPath) {
      fetchDirectory(parentPath)
    }
  }

  return (
    <div className="border border-slate-800 bg-slate-950 p-4 font-mono text-xs text-cyan-100">
      <div className="flex justify-between items-center border-b border-slate-800 pb-2 mb-3">
        <span className="text-fuchsia-400 font-bold uppercase tracking-widest">// SELECT DIRECTORY (选择绝对路径)</span>
        <button onClick={onClose} className="text-slate-500 hover:text-cyan-400">[CLOSE]</button>
      </div>

      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={currentPath}
          onChange={(e) => setCurrentPath(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && fetchDirectory(currentPath)}
          className="flex-1 border border-slate-800 bg-slate-900/50 px-3 py-1.5 text-cyan-200 outline-none"
        />
        <button
          onClick={() => fetchDirectory(currentPath)}
          className="border border-slate-700 hover:border-cyan-500 px-4 py-1.5 uppercase font-bold"
        >
          Go
        </button>
      </div>

      {error && <p className="text-red-400 mb-3">{error}</p>}

      {loading ? (
        <p className="py-6 text-center animate-pulse text-slate-500">// READING DISK DIRECTORY FILES...</p>
      ) : (
        <div className="space-y-1 max-h-48 overflow-y-auto border border-slate-900 bg-black/30 p-2">
          {parentPath && (
            <div
              onClick={handleGoParent}
              className="py-1 px-2 hover:bg-slate-900/60 text-fuchsia-400 cursor-pointer font-bold"
            >
              [..] (返回上一级目录)
            </div>
          )}
          {subdirs.length === 0 ? (
            <p className="p-2 text-slate-500">// No subdirectories here.</p>
          ) : (
            subdirs.map((dir) => (
              <div
                key={dir}
                onClick={() => handleSelectSubdir(dir)}
                className="py-1 px-2 hover:bg-slate-900/60 text-cyan-100 cursor-pointer"
              >
                📁 {dir}/
              </div>
            ))
          )}
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-slate-800 flex justify-end gap-3">
        <button
          onClick={() => onSelect(currentPath)}
          className="border border-fuchsia-500 hover:bg-fuchsia-500/15 text-fuchsia-400 font-bold px-6 py-2 uppercase"
        >
          [SELECT CURRENT / 选定当前目录]
        </button>
      </div>
    </div>
  )
}
