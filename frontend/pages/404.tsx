import Link from 'next/link'

export default function Custom404() {
  return (
    <div className="flex flex-col items-center justify-center py-32">
      <h1 className="font-mono text-6xl font-bold text-cyan-400">404</h1>
      <p className="mt-4 font-mono text-slate-400">PAGE NOT FOUND</p>
      <Link
        href="/"
        className="mt-8 border border-cyan-500 px-6 py-2 font-mono text-sm text-cyan-400 hover:bg-cyan-500/10"
      >
        RETURN TO BASE
      </Link>
    </div>
  )
}
