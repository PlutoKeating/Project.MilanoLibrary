import React from 'react'
import { TaskStatus } from '../hooks/useSummarize'

interface TimelineProgressProps {
  taskStatus: TaskStatus | null
}

export function TimelineProgress({ taskStatus }: TimelineProgressProps) {
  if (!taskStatus) {
    return (
      <div className="mt-8 border border-dashed border-neutral-800 p-4 text-center font-mono text-xs text-neutral-500">
        <span className="animate-pulse">INITIALIZING PIPELINE COMPOSER...</span>
      </div>
    )
  }

  const { steps, flow_type } = taskStatus

  return (
    <div className="mt-8 border border-cyan-500/30 bg-[#0a0a0f] p-6 font-mono text-sm">
      <div className="mb-4 flex items-center justify-between border-b border-cyan-500/20 pb-2">
        <span className="text-xs text-neutral-500">PIPELINE MONITOR [FLOW: {flow_type.toUpperCase()}]</span>
        <span className="animate-pulse text-xs text-cyan-400 font-semibold">ONLINE</span>
      </div>

      <div className="relative pl-6">
        {/* Vertical connector line */}
        <div className="absolute left-[7px] top-2 bottom-2 w-[1px] bg-neutral-800" />

        {steps.map((step) => {
          const isPending = step.status === 'pending'
          const isRunning = step.status === 'running'
          const isCompleted = step.status === 'completed'
          const isFailed = step.status === 'failed'

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
          }

          return (
            <div key={step.id} className="relative mb-6 last:mb-0">
              {/* Timeline dot */}
              <div
                className={`absolute -left-[24px] top-[4px] h-3.5 w-3.5 border ${borderClass} ${bgClass}`}
                style={{ transform: 'translateX(-1.5px)' }}
              />

              <div className={`border-l-2 pl-4 ${isRunning ? 'border-cyan-500' : isCompleted ? 'border-fuchsia-500' : isFailed ? 'border-red-500' : 'border-neutral-800'}`}>
                <div className="flex items-center justify-between">
                  <span className={`${statusClass} text-xs tracking-wider font-semibold uppercase`}>
                    {statusSymbol} {step.title}
                  </span>
                  {isRunning && step.progress > 0 && (
                    <span className="text-xs text-cyan-400 font-bold">{Math.round(step.progress)}%</span>
                  )}
                </div>

                {step.message && (
                  <div className={`mt-1.5 text-xs ${isRunning ? 'text-cyan-300' : isFailed ? 'text-red-400' : 'text-neutral-400'}`}>
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
    </div>
  )
}
