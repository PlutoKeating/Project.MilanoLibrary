import React from 'react'

export default function Header() {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-[#0a0a0f]/90">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <a href="/" className="font-mono text-lg font-bold tracking-wider text-cyan-400">
          ▣ MILANO LIBRARY
        </a>
        <span className="font-mono text-xs tracking-widest text-slate-500">v2.0</span>
      </div>
    </header>
  )
}
