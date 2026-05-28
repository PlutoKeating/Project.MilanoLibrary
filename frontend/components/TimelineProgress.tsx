import React, { useEffect, useState } from 'react'
import { TaskStatus } from '../hooks/useSummarize'
import { pausePipeline, stopPipeline } from '../lib/api'

function getApiBaseUrl() {
  if (typeof window !== 'undefined') {
    const stored = window.localStorage.getItem('backend-base-url')
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        if (parsed) {
          return typeof parsed === 'string' ? parsed.replace(/\/$/, '') : parsed
        }
      } catch (e) {
        return stored
      }
    }
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
}

interface TimelineProgressProps {
  taskStatus?: TaskStatus | null
  taskId?: string | null
}

export function TimelineProgress({ taskStatus: propTaskStatus, taskId }: TimelineProgressProps) {
  const [internalStatus, setInternalStatus] = useState<TaskStatus | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    if (!taskId) {
      setInternalStatus(null)
      setNotFound(false)
      return
    }

    let pollInterval: any = null
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/status/${taskId}`)
        if (res.ok) {
          const data = await res.json()
          setInternalStatus(data)
          setNotFound(false)
          
          const allDone = data.steps?.every((step: any) => step.status === 'completed' || step.status === 'failed') ||
                          data.is_paused ||
                          data.is_stopped ||
                          data.steps?.some((step: any) => step.status === 'paused' || step.status === 'cancelled' || step.status === 'stopped')
          if (allDone) {
            clearInterval(pollInterval)
          }
        } else if (res.status === 404) {
          setNotFound(true)
        }
      } catch (err) {
        console.error('Error fetching pipeline status:', err)
      }
    }

    fetchStatus()
    pollInterval = setInterval(fetchStatus, 1000)

    return () => {
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [taskId])

  const handlePause = async () => {
    if (!taskId) return
    setActionLoading(true)
    try {
      await pausePipeline(taskId)
      const res = await fetch(`${getApiBaseUrl()}/api/status/${taskId}`)
      if (res.ok) {
        const data = await res.json()
        setInternalStatus(data)
      }
    } catch (err: any) {
      alert(`PAUSE ERROR: ${err.message || err}`)
    } finally {
      setActionLoading(false)
    }
  }

  const handleStop = async () => {
    if (!taskId) return
    if (!confirm('ARE YOU SURE YOU WANT TO STOP THE PIPELINE AND CLEAR ALL RUNTIME CACHE?')) {
      return
    }
    setActionLoading(true)
    try {
      await stopPipeline(taskId)
      const res = await fetch(`${getApiBaseUrl()}/api/status/${taskId}`)
      if (res.ok) {
        const data = await res.json()
        setInternalStatus(data)
      }
    } catch (err: any) {
      alert(`STOP ERROR: ${err.message || err}`)
    } finally {
      setActionLoading(false)
    }
  }

  const status = taskId ? (internalStatus || propTaskStatus) : propTaskStatus

  if (notFound) {
    return null
  }

  if (!status) {
    return (
      <div className="mt-8 border border-dashed border-neutral-800 p-4 text-center font-mono text-xs text-neutral-500">
        <span className="animate-pulse">INITIALIZING PIPELINE COMPOSER...</span>
      </div>
    )
  }

  const { steps, flow_type } = status

  const isPipelineRunning = !!taskId && !!status && status.steps?.some(step => step.status === 'running') && !status.is_paused && !status.is_stopped

  return (
    <div className="mt-8 border border-cyan-500/30 bg-[#0a0a0f] p-6 font-mono text-sm">
      <div className="mb-4 flex items-center justify-between border-b border-cyan-500/20 pb-2">
        <span className="text-xs text-neutral-500">PIPELINE MONITOR [FLOW: {flow_type.toUpperCase()}]</span>
        {status.is_paused ? (
          <span className="text-xs text-yellow-500 font-semibold uppercase">PAUSED</span>
        ) : status.is_stopped ? (
          <span className="text-xs text-neutral-500 font-semibold uppercase">STOPPED</span>
        ) : isPipelineRunning ? (
          <span className="animate-pulse text-xs text-cyan-400 font-semibold uppercase">ONLINE</span>
        ) : (
          <span className="text-xs text-fuchsia-500 font-semibold uppercase">FINISHED</span>
        )}
      </div>

      <div className="relative pl-6">
        {/* Vertical connector line */}
        <div className="absolute left-[7px] top-2 bottom-2 w-[1px] bg-neutral-800" />

        {steps.map((step) => {
          const isPending = step.status === 'pending'
          const isRunning = step.status === 'running'
          const isCompleted = step.status === 'completed'
          const isFailed = step.status === 'failed'
          const isPaused = step.status === 'paused'
          const isCancelled = step.status === 'cancelled' || step.status === 'stopped'

          let statusSymbol = '[ ]'
          let statusClass = 'text-neutral-500'
          let borderClass = 'border-neutral-800'
          let bgClass = 'bg-[#0a0a0f]'

          if (isRunning) {
            statusSymbol = '[>]'
            statusClass = 'text-cyan-400 font-bold'
            borderClass = 'border-cyan-500 shadow-[0_0_8px_rgba(0,240,255,0.2)]'
            bgClass = 'bg-cyan-950/20'
          } else if (isCompleted) {
            statusSymbol = '[x]'
            statusClass = 'text-fuchsia-500'
            borderClass = 'border-fuchsia-500'
          } else if (isFailed) {
            statusSymbol = '[!]'
            statusClass = 'text-red-500 font-bold'
            borderClass = 'border-red-500'
            bgClass = 'bg-red-950/10'
          } else if (isPaused) {
            statusSymbol = '[||]'
            statusClass = 'text-yellow-500 font-bold'
            borderClass = 'border-yellow-500'
            bgClass = 'bg-yellow-950/10'
          } else if (isCancelled) {
            statusSymbol = '[#]'
            statusClass = 'text-neutral-500 font-bold'
            borderClass = 'border-neutral-800'
            bgClass = 'bg-neutral-950/10'
          }

          return (
            <div key={step.id} className="relative mb-6 last:mb-0">
              {/* Timeline dot */}
              <div
                className={`absolute -left-[24px] top-[4px] h-3.5 w-3.5 border ${borderClass} ${bgClass}`}
                style={{ transform: 'translateX(-1.5px)' }}
              />

              <div className={`border-l-2 pl-4 ${isRunning ? 'border-cyan-500' : isCompleted ? 'border-fuchsia-500' : isFailed ? 'border-red-500' : isPaused ? 'border-yellow-500' : isCancelled ? 'border-neutral-800/50' : 'border-neutral-800'}`}>
                <div className="flex items-center justify-between">
                  <span className={`${statusClass} text-xs tracking-wider font-semibold uppercase`}>
                    {statusSymbol} {step.title}
                  </span>
                  {isRunning && step.progress > 0 && (
                    <span className="text-xs text-cyan-400 font-bold">{Math.round(step.progress)}%</span>
                  )}
                </div>

                {step.message && (
                  <div className={`mt-1.5 text-xs ${isRunning ? 'text-cyan-300' : isFailed ? 'text-red-400' : isPaused ? 'text-yellow-400' : 'text-neutral-400'}`}>
                    &gt; {step.message}
                  </div>
                )}

                {/* mini progress bar for running/processing step */}
                {isRunning && step.progress > 0 && (
                  <div className="mt-2 h-[2px] w-full bg-neutral-900">
                    <div
                      className="h-full bg-cyan-400 transition-all duration-300 ease-out"
                      style={{ width: `${step.progress}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {isPipelineRunning && (
        <div className="mt-6 flex gap-4 border-t border-cyan-500/20 pt-4">
          <button
            onClick={handlePause}
            disabled={actionLoading}
            className="border border-yellow-500 bg-[#0a0a0f] px-4 py-2 text-xs text-yellow-500 font-bold hover:bg-yellow-950/20 active:bg-yellow-950/40 transition-colors disabled:opacity-50"
          >
            // PAUSE PIPELINE //
          </button>
          <button
            onClick={handleStop}
            disabled={actionLoading}
            className="border border-fuchsia-500 bg-[#0a0a0f] px-4 py-2 text-xs text-fuchsia-500 font-bold hover:bg-fuchsia-950/20 active:bg-fuchsia-950/40 transition-colors disabled:opacity-50"
          >
            // STOP & CLEAR CACHE //
          </button>
        </div>
      )}
    </div>
  )
}
