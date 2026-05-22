import React from 'react'

export function SubmitButton({ loading }: { loading: boolean }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="mt-6 w-full border border-cyan-500 bg-transparent py-3 font-mono text-sm tracking-wider text-cyan-400 hover:bg-cyan-500/10 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {loading ? <span className="animate-pulse">PROCESSING...</span> : 'EXECUTE SUMMARY'}
    </button>
  )
}
