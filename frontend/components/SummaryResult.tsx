import React, { useMemo, useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import { ActionsAfterResult } from '~/components/ActionsAfterResult'
import { formatSummary } from '~/utils/summary'

interface HeadingItem {
  id: string
  text: string
  level: number
}

function getTextFromChildren(children: React.ReactNode): string {
  if (!children) return ''
  if (typeof children === 'string') return children
  if (typeof children === 'number') return String(children)
  if (Array.isArray(children)) {
    return children.map(getTextFromChildren).join('')
  }
  if (typeof children === 'object' && 'props' in children) {
    return getTextFromChildren((children as any).props.children)
  }
  return ''
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^\w\-\u4e00-\u9fa5]+/g, '')
    .replace(/\-\-+/g, '-')
    .replace(/^-+/, '')
    .replace(/-+$/, '')
}

function preprocessLatex(text: string): string {
  if (!text) return ''
  return text
    .replace(/\\\\\(/g, '$')
    .replace(/\\\\\)/g, '$')
    .replace(/\\\\\[/g, '$$')
    .replace(/\\\\\]/g, '$$')
    .replace(/\\\(/g, '$')
    .replace(/\\\)/g, '$')
    .replace(/\\\[/g, '$$')
    .replace(/\\\]/g, '$$')
}

function replaceTimestampsWithLinks(
  text: string,
  videoId: string,
  videoUrl: string,
  enabled: boolean,
): string {
  if (!enabled || !videoUrl || !videoId) return text

  const isBiliBili = videoUrl.includes('bilibili.com')
  const baseUrl = isBiliBili
    ? `https://www.bilibili.com/video/${videoId}/?t=`
    : `https://youtube.com/watch?v=${videoId}&t=`

  return text.replace(/\[(\d{1,2}:\d{2}(?::\d{2})?)\]/g, (match, ts) => {
    const parts = ts.split(':').map(Number)
    let seconds = 0
    if (parts.length === 2) {
      seconds = parts[0] * 60 + parts[1]
    } else if (parts.length === 3) {
      seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
    }
    const href = `${baseUrl}${seconds}`
    return `[${match}](${href})`
  })
}

export function SummaryResult({
  currentVideoUrl,
  currentVideoId,
  summary,
  shouldShowTimestamp,
}: {
  currentVideoUrl: string
  currentVideoId: string
  summary: string
  shouldShowTimestamp?: boolean
}) {
  const formattedCachedSummary = useMemo(() => {
    return summary?.startsWith('"')
      ? summary
          .substring(1, summary.length - 1)
          .split('\\n')
          .join('\n')
      : summary
  }, [summary])

  const { formattedSummary } = useMemo(() => {
    return formatSummary(formattedCachedSummary)
  }, [formattedCachedSummary])

  const handleCopy = () => {
    if (typeof navigator !== 'undefined') {
      navigator.clipboard.writeText(formattedSummary)
    }
  }

  const isLocalVideo = !currentVideoUrl || currentVideoUrl === ''

  // Preprocess LaTeX math formulas
  const preprocessedLatex = useMemo(() => {
    return preprocessLatex(formattedCachedSummary || '')
  }, [formattedCachedSummary])

  // Preprocess timestamps in text
  const finalSummaryText = useMemo(() => {
    return replaceTimestampsWithLinks(preprocessedLatex, currentVideoId, currentVideoUrl, !!shouldShowTimestamp)
  }, [preprocessedLatex, currentVideoId, currentVideoUrl, shouldShowTimestamp])

  // Extract all headings for Table of Contents
  const headings = useMemo(() => {
    if (!finalSummaryText) return []
    const list: HeadingItem[] = []
    const lines = finalSummaryText.split('\n')
    for (const line of lines) {
      // Find markdown headings
      const match = line.match(/^(#{1,6})\s+(.*)$/)
      if (match) {
        const level = match[1].length
        let text = match[2].trim()
        
        // Strip markdown links if any in the heading text for TOC presentation
        // e.g., `[[00:12]](url) Intro` -> `[00:12] Intro`
        text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        
        const id = slugify(text)
        list.push({ id, text, level })
      }
    }
    return list
  }, [finalSummaryText])

  const [activeId, setActiveId] = useState<string>('')

  // IntersectionObserver to highlight active TOC heading
  useEffect(() => {
    if (headings.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntries = entries.filter((entry) => entry.isIntersecting)
        if (visibleEntries.length > 0) {
          // Sort visible entries by their proximity to the top of the viewport
          const sorted = visibleEntries.sort((a, b) => {
            return Math.abs(a.boundingClientRect.top - 120) - Math.abs(b.boundingClientRect.top - 120)
          })
          setActiveId(sorted[0].target.id)
        }
      },
      {
        rootMargin: '-100px 0px -60% 0px',
      }
    )

    headings.forEach((heading) => {
      const el = document.getElementById(heading.id)
      if (el) observer.observe(el)
    })

    return () => {
      observer.disconnect()
    }
  }, [headings])

  const handleTocClick = (id: string) => {
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' })
    }
  }

  return (
    <div className="flex flex-col lg:flex-row gap-8 items-start mt-12 w-full">
      {/* Table of Contents Sidebar */}
      {headings.length > 0 && (
        <aside className="w-full lg:w-64 shrink-0 lg:sticky lg:top-20 max-h-[calc(100vh-8rem)] overflow-y-auto border border-slate-800 bg-[#0a0a0f] p-4">
          <h4 className="font-mono text-xs font-bold tracking-widest text-fuchsia-400 uppercase mb-4 border-b border-slate-800 pb-2">
            目录 / CONTENTS
          </h4>
          <nav className="space-y-1">
            {headings.map((heading) => {
              const isActive = activeId === heading.id
              return (
                <button
                  key={heading.id}
                  onClick={() => handleTocClick(heading.id)}
                  className={`block w-full text-left font-mono text-xs transition-all py-1 hover:text-cyan-400 ${
                    heading.level === 3 ? 'pl-3 border-l border-slate-800' : ''
                  } ${heading.level === 4 ? 'pl-6 border-l border-slate-800' : ''} ${
                    heading.level >= 5 ? 'pl-9 border-l border-slate-800' : ''
                  } ${
                    isActive
                      ? 'text-cyan-400 font-bold border-l-2 border-cyan-400 pl-2 -ml-[1px]'
                      : 'text-slate-400'
                  }`}
                >
                  {heading.text}
                </button>
              )
            })}
          </nav>
        </aside>
      )}

      {/* Main Markdown Content Box */}
      <div className="flex-1 min-w-0 w-full border border-slate-800 bg-slate-900/5">
        <div className="border-b border-slate-800 bg-slate-900/30 px-4 py-2 flex items-center justify-between">
          {isLocalVideo ? (
            <span className="font-mono text-xs text-cyan-400">▶ {currentVideoId || '本地视频'}</span>
          ) : (
            <a
              href={currentVideoUrl}
              target="_blank"
              rel="noreferrer"
              className="font-mono text-xs text-cyan-400 hover:text-cyan-300"
            >
              ▶ {currentVideoId}
            </a>
          )}
        </div>
        <div className="p-4">
          <div className="markdown-body chapter-section">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                h1: ({ children, ...props }: any) => {
                  const text = getTextFromChildren(children)
                  const id = slugify(text)
                  return <h1 id={id} className="scroll-mt-24 font-mono font-bold text-cyan-400 mb-4 pb-2 border-b border-slate-800" {...props}>{children}</h1>
                },
                h2: ({ children, ...props }: any) => {
                  const text = getTextFromChildren(children)
                  const id = slugify(text)
                  return <h2 id={id} className="scroll-mt-24 font-mono font-bold text-cyan-400 mb-4 pb-2 border-b border-slate-800" {...props}>{children}</h2>
                },
                h3: ({ children, ...props }: any) => {
                  const text = getTextFromChildren(children)
                  const id = slugify(text)
                  return <h3 id={id} className="scroll-mt-24 font-mono font-bold text-cyan-400 mb-3 pb-1 border-b border-slate-800/50" {...props}>{children}</h3>
                },
                h4: ({ children, ...props }: any) => {
                  const text = getTextFromChildren(children)
                  const id = slugify(text)
                  return <h4 id={id} className="scroll-mt-24 font-mono font-bold text-fuchsia-400 mb-2" {...props}>{children}</h4>
                },
                h5: ({ children, ...props }: any) => {
                  const text = getTextFromChildren(children)
                  const id = slugify(text)
                  return <h5 id={id} className="scroll-mt-24 font-mono font-bold mb-2" {...props}>{children}</h5>
                },
                h6: ({ children, ...props }: any) => {
                  const text = getTextFromChildren(children)
                  const id = slugify(text)
                  return <h6 id={id} className="scroll-mt-24 font-mono font-bold mb-2" {...props}>{children}</h6>
                },
                a: ({ href, children, ...props }: any) => {
                  const isTimestamp = href?.includes('t=')
                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={isTimestamp ? 'text-cyan-400 hover:text-cyan-300 font-mono text-xs' : 'text-cyan-400 hover:underline'}
                      {...props}
                    >
                      {children}
                    </a>
                  )
                }
              }}
            >
              {finalSummaryText}
            </ReactMarkdown>
          </div>
        </div>
        <ActionsAfterResult curVideo={currentVideoUrl} onCopy={handleCopy} summaryNote={formattedSummary} />
      </div>
    </div>
  )
}
