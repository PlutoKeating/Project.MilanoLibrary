import React from 'react'

export function ActionsAfterResult({
  curVideo,
  onCopy,
}: {
  curVideo: string
  summaryNote: string
  onCopy: () => void
}) {
  return (
    <div className="flex gap-2 border-t border-slate-800 px-4 py-3">
      <button
        onClick={onCopy}
        className="border border-slate-700 px-3 py-1 font-mono text-xs text-slate-400 hover:border-cyan-500 hover:text-cyan-400"
      >
        COPY
      </button>
      <a
        href={curVideo}
        target="_blank"
        rel="noreferrer"
        className="border border-slate-700 px-3 py-1 font-mono text-xs text-slate-400 hover:border-cyan-500 hover:text-cyan-400"
      >
        VIDEO
      </a>
    </div>
  )
}
