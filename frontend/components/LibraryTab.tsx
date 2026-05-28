import React, { useMemo, useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

import { PipelineProcessor } from '~/components/PipelineProcessor'
import { TimelineProgress } from '~/components/TimelineProgress'
import { getApiBaseUrl } from '~/lib/api'

interface MilanoParagraph {
  id?: number
  start_time: number
  end_time: number
  text_content: string
  multi_modal_data?: any
}

interface MilanoItem {
  id?: number
  type: 'StuffList' | 'Timeline' | 'RelationGraph'
  name: string
  description: string
  payload: any
}

interface MilanoBook {
  id: string
  title: string
  author: string
  description?: string
  source_url?: string
  media_type: string
  media_path?: string
  audio_path?: string
  duration_seconds: number
  created_at: string
  updated_at: string
  paragraphs?: MilanoParagraph[]
  items?: MilanoItem[]
}

interface LibraryTabProps {
  books: MilanoBook[]
  fetchBooks: () => Promise<void>
  vaultPath: string
  handleDirectCreateBook: () => Promise<void>
  handleDeleteBook: (bookId: string, e?: React.MouseEvent) => Promise<void>
}

const extractTextFromReactNode = (node: any): string => {
  if (!node) return ''
  if (typeof node === 'string') return node
  if (typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(extractTextFromReactNode).join('')
  if (node.props && node.props.children) return extractTextFromReactNode(node.props.children)
  return ''
}

const headingRenderer = (level: number) => {
  return ({ children, ...props }: any) => {
    const text = extractTextFromReactNode(children)
    const id = text.toLowerCase()
      .trim()
      .replace(/\s+/g, '-')
      .replace(/[^\w-]/g, '')
    const Tag = `h${level}` as any
    
    if (level === 1) {
      return (
        <div className="border-l-4 border-cyan-400 bg-cyan-950/10 px-4 py-2 mt-8 mb-4">
          <Tag id={id} className="font-mono text-base font-bold uppercase tracking-wider text-cyan-400" {...props}>
            {children}
          </Tag>
        </div>
      )
    } else if (level === 2) {
      return (
        <div className="border-b border-fuchsia-950 pb-1 mt-6 mb-3">
          <Tag id={id} className="font-mono text-sm font-bold text-fuchsia-400 flex items-center gap-2" {...props}>
            {children}
          </Tag>
        </div>
      )
    } else if (level === 3) {
      return (
        <div className="mt-5 mb-2 pl-3 border-l-2 border-slate-800">
          <Tag id={id} className="font-mono text-xs font-bold text-cyan-300 flex items-center gap-1.5" {...props}>
            {children}
          </Tag>
        </div>
      )
    } else if (level === 4) {
      return (
        <Tag id={id} className="font-mono text-[11px] font-bold text-slate-200 mt-4 mb-2 flex items-center gap-1" {...props}>
          {children}
        </Tag>
      )
    } else {
      return (
        <Tag id={id} className="font-mono text-[10px] font-bold text-slate-400 mt-3 mb-1" {...props}>
          {children}
        </Tag>
      )
    }
  }
}

const markdownComponents = {
  h1: headingRenderer(1),
  h2: headingRenderer(2),
  h3: headingRenderer(3),
  h4: headingRenderer(4),
  h5: headingRenderer(5),
  h6: headingRenderer(6),
  p: ({ children }: any) => <p className="font-mono text-xs text-slate-300 leading-relaxed mb-4">{children}</p>,
  ul: ({ children }: any) => <ul className="list-disc pl-5 space-y-1 mb-4 font-mono text-xs text-slate-300">{children}</ul>,
  ol: ({ children }: any) => <ol className="list-decimal pl-5 space-y-1 mb-4 font-mono text-xs text-slate-300">{children}</ol>,
  li: ({ children }: any) => <li className="leading-relaxed">{children}</li>,
  code: ({ node, inline, className, children, ...props }: any) => {
    const match = /language-(\w+)/.exec(className || '')
    return !inline ? (
      <pre className="border border-slate-800 bg-black/40 p-4 rounded-none overflow-x-auto my-4 text-[11px] leading-normal font-mono text-cyan-100/95">
        <code className={className} {...props}>
          {children}
        </code>
      </pre>
    ) : (
      <code className="bg-slate-950 px-1.5 py-0.5 border border-slate-900 font-mono text-[11px] text-fuchsia-400" {...props}>
        {children}
      </code>
    )
  }
}

export default function LibraryTab({
  books,
  fetchBooks,
  vaultPath,
  handleDirectCreateBook,
  handleDeleteBook
}: LibraryTabProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [bookDetails, setBookDetails] = useState<MilanoBook | null>(null)
  const [bookContent, setBookContent] = useState<string>('')
  const [bookIndex, setBookIndex] = useState<any>(null)
  const [showInlineCompiler, setShowInlineCompiler] = useState(false)
  const [isRecompiling, setIsRecompiling] = useState(false)
  
  const videoPlayerRef = useRef<HTMLVideoElement>(null)

  const fetchBookContent = async (bookId: string) => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/books/${bookId}/content`)
      if (res.ok) {
        const data = await res.json()
        setBookContent(data.content || '')
      }
    } catch (e) {
      console.error('Error fetching book content:', e)
    }
  }

  const fetchBookIndex = async (bookId: string) => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/books/${bookId}/index`)
      if (res.ok) {
        const data = await res.json()
        setBookIndex(data)
      } else {
        setBookIndex(null)
      }
    } catch (e) {
      console.error('Error fetching book index:', e)
      setBookIndex(null)
    }
  }

  const fetchBookDetails = async (bookId: string) => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/books/${bookId}`)
      if (res.ok) {
        const data = await res.json()
        setBookDetails(data)
        await fetchBookContent(bookId)
        await fetchBookIndex(bookId)
      }
    } catch (e) {
      console.error('Error fetching book details:', e)
    }
  }

  const handleRecompileBook = async (bookId: string) => {
    setIsRecompiling(true)
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/books/${bookId}/compile`, {
        method: 'POST'
      })
      if (res.ok) {
        alert('RE-COMPILATION SUCCESSFUL / 编译拼装成功！')
        await fetchBookContent(bookId)
      } else {
        const err = await res.json()
        alert(`RE-COMPILATION FAILED: ${err.detail || 'UNKNOWN ERROR'}`)
      }
    } catch (e: any) {
      console.error(e)
      alert(`ERROR DURING RE-COMPILATION: ${e.message}`)
    } finally {
      setIsRecompiling(false)
    }
  }

  const handleOpenBookTerminal = async (bookId: string) => {
    setBookDetails(null)
    setShowInlineCompiler(false)
    await fetchBookDetails(bookId)
  }

  const filteredBooks = useMemo(() => {
    return books.filter(b => 
      b.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.author.toLowerCase().includes(searchQuery.toLowerCase())
    )
  }, [books, searchQuery])

  const renderOutlineTree = (outlineList: any[], indices: number[] = [], depth: number = 0): React.ReactNode => {
    if (!outlineList) return null
    return (
      <div className={`space-y-1 ${depth > 0 ? 'ml-3 border-l border-slate-900 pl-2' : ''}`}>
        {outlineList.map((node: any, idx: number) => {
          const currentIndices = [...indices, idx + 1]
          
          let prefix = ''
          if (currentIndices.length === 1) {
            const cnNums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十"]
            const cIdx = currentIndices[0] - 1
            const cnStr = cIdx < cnNums.length ? cnNums[cIdx] : String(currentIndices[0])
            prefix = `${cnStr}、`
          } else {
            prefix = currentIndices.join('.') + '. '
          }
          
          const fullTitle = `${prefix}${node.title}`
          const headingId = fullTitle.toLowerCase().trim().replace(/\s+/g, '-').replace(/[^\w-]/g, '')
          const hasChildren = node.children && node.children.length > 0
          
          return (
            <div key={node.id || node.title} className="space-y-1">
              <button
                onClick={() => {
                  const el = document.getElementById(headingId)
                  if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
                  } else {
                    console.warn(`Element with ID '${headingId}' not found in DOM`)
                  }
                }}
                className={`w-full text-left font-mono hover:text-cyan-400 hover:bg-slate-900/40 transition-all block px-1.5 py-1 text-ellipsis overflow-hidden whitespace-nowrap ${
                  depth === 0 ? 'text-xs font-bold text-cyan-300' :
                  depth === 1 ? 'text-[11px] text-fuchsia-400 font-medium' :
                  'text-[10px] text-slate-400'
                }`}
                title={fullTitle}
              >
                {fullTitle}
              </button>
              {hasChildren && renderOutlineTree(node.children, currentIndices, depth + 1)}
            </div>
          )
        })}
      </div>
    )
  }

  const handleTabDeleteBook = async (bookId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    const deleted = await handleDeleteBook(bookId, e)
    // Wait, let's see, if deletion was successful and bookDetails was open for this book, close details.
    if (bookDetails?.id === bookId) {
      setBookDetails(null)
    }
  }

  return (
    <div className="w-full">
      {/* --- LIBRARY TAB --- */}
      {!bookDetails && (
        <div className="mt-8 space-y-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <input
              type="text"
              placeholder="搜索标题或作者..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full sm:w-80 border border-slate-800 bg-slate-900/40 px-4 py-2 font-mono text-xs text-cyan-100 outline-none focus:border-cyan-500"
            />
            <span className="font-mono text-[10px] text-slate-500 uppercase tracking-wider">
              CURRENT VAULT PATH: {vaultPath || 'DEFAULT'}
            </span>
          </div>

          {/* Books Shelf Grid using Book-Shaped Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 pt-4">
            
            {/* Special Create Book Card (Book-Shaped with '+' inside) */}
            <div
              onClick={handleDirectCreateBook}
              className="group cursor-pointer border border-dashed border-cyan-700/50 hover:border-cyan-400 bg-slate-950/20 aspect-[3/4] flex flex-row transition-all duration-300 hover:-translate-y-1"
            >
              {/* Thick Spine Binding Mimic */}
              <div className="w-6 shrink-0 bg-cyan-950/20 border-r border-slate-900/60 flex flex-col justify-between items-center py-4 text-[9px] font-mono text-cyan-500 font-bold border-l-4 border-l-cyan-500 select-none">
                  <span>S</span>
                  <span>P</span>
                  <span>I</span>
                  <span>N</span>
                  <span>E</span>
                </div>
              {/* Internal container with '+' */}
              <div className="flex-1 flex flex-col justify-center items-center p-4">
                <span className="font-mono text-5xl text-cyan-400 group-hover:scale-110 transition-transform duration-200 font-light">
                  +
                </span>
                <span className="mt-4 font-mono text-[10px] text-cyan-500 font-bold uppercase tracking-widest text-center leading-relaxed">
                  [ NEW VAULT ]<br />创建新书籍
                </span>
              </div>
            </div>

            {/* Existing MilanoBooks List */}
            {filteredBooks.map((book) => (
              <div
                key={book.id}
                onClick={() => handleOpenBookTerminal(book.id)}
                className="group cursor-pointer border border-slate-800 hover:border-fuchsia-500 bg-[#09090e] aspect-[3/4] flex flex-row transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-fuchsia-950/20"
              >
                <div className="w-6 shrink-0 bg-fuchsia-950/20 border-r border-slate-900/60 flex flex-col justify-between items-center py-4 text-[9px] font-mono text-fuchsia-500 font-bold border-l-4 border-l-fuchsia-500 select-none">
                  <span>M</span>
                  <span>I</span>
                  <span>L</span>
                  <span>A</span>
                  <span>N</span>
                  <span>O</span>
                </div>
                
                <div className="flex-1 p-4 flex flex-col justify-between overflow-hidden">
                  <div className="space-y-2">
                    <span className="font-mono text-[9px] bg-slate-800 text-slate-300 px-1.5 py-0.5 uppercase tracking-wider font-bold">
                      {book.media_type === 'local' ? 'LOCAL' : 'LINK'}
                    </span>
                    <h3 className="font-mono text-xs font-bold text-cyan-100 group-hover:text-cyan-400 line-clamp-3 leading-snug">
                      {book.title}
                    </h3>
                    <p className="font-mono text-[10px] text-fuchsia-400 line-clamp-1">
                      @{book.author}
                    </p>
                  </div>

                  <div className="space-y-2 border-t border-slate-900 pt-2 font-mono text-[9px] text-slate-500">
                    <p>Time: {(book.duration_seconds / 60).toFixed(1)}m</p>
                    <p className="line-clamp-1">{new Date(book.created_at).toLocaleDateString()}</p>
                    
                    <div className="pt-2 flex justify-between items-center text-[10px] text-cyan-400">
                      <span>[READ]</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleTabDeleteBook(book.id); }}
                        className="text-slate-600 hover:text-red-400 transition-colors"
                      >
                        [DELETE]
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* --- BOOK DETAIL TERMINAL VIEW --- */}
      {bookDetails && (
        <div className="mt-8 space-y-6">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-900 pb-4">
            <button
              onClick={() => setBookDetails(null)}
              className="font-mono text-xs text-slate-400 hover:text-cyan-400"
            >
              [&lt;- BACK TO SHELVES / 返回书架]
            </button>
            
            <div className="flex gap-4">
              <button
                onClick={() => setShowInlineCompiler(!showInlineCompiler)}
                className={`border px-4 py-1.5 font-mono text-xs transition-colors uppercase ${
                  showInlineCompiler ? 'border-cyan-400 bg-cyan-950/20 text-cyan-300' : 'border-fuchsia-500 text-fuchsia-400 hover:bg-fuchsia-500/10'
                }`}
              >
                {showInlineCompiler ? '[CLOSE COMPILER / 关闭处理器]' : '[RE-PROCESS / 覆盖重新加工]'}
              </button>
              <button
                onClick={() => handleRecompileBook(bookDetails.id)}
                disabled={isRecompiling}
                className="border border-cyan-500 text-cyan-400 hover:bg-cyan-950/20 px-4 py-1.5 font-mono text-xs disabled:opacity-50 transition-colors"
              >
                {isRecompiling ? '[COMPILING... / 编译中...]' : '[RE-COMPILE / 重新编译大纲]'}
              </button>
              <button
                onClick={() => handleTabDeleteBook(bookDetails.id)}
                className="border border-slate-800 hover:border-red-500 hover:text-red-400 px-4 py-1.5 font-mono text-xs text-slate-400 transition-colors"
              >
                [DELETE VAULT / 销毁该书]
              </button>
            </div>
          </div>

          {/* Book Metadata Jumbotron */}
          <div className="border border-slate-800 bg-slate-900/10 p-6">
            <h2 className="font-mono text-xl font-bold text-cyan-400">{bookDetails.title}</h2>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2 font-mono text-xs">
              <p><span className="text-slate-500">Author:</span> <span className="text-fuchsia-400">{bookDetails.author}</span></p>
              <p><span className="text-slate-500">Duration:</span> <span className="text-cyan-100">{(bookDetails.duration_seconds / 60).toFixed(2)} mins</span></p>
              <p><span className="text-slate-500">UUID:</span> <span className="text-cyan-100/70">{bookDetails.id}</span></p>
            </div>
            {bookDetails.source_url && (
              <p className="mt-3 font-mono text-xs">
                <span className="text-slate-500">Origin URL:</span>{' '}
                <a href={bookDetails.source_url} target="_blank" rel="noreferrer" className="text-cyan-400 hover:underline break-all">
                  {bookDetails.source_url}
                </a>
              </p>
            )}
            {bookDetails.description && (
              <p className="mt-4 font-mono text-xs text-slate-400 leading-relaxed max-w-4xl border-t border-slate-900 pt-3">
                {bookDetails.description}
              </p>
            )}
          </div>

          {!(showInlineCompiler || bookDetails.duration_seconds === 0) && (
            <TimelineProgress taskId={bookDetails.id} />
          )}

          {/* MERGED INLINE VIDEO COMPILER PANELS */}
          {(showInlineCompiler || bookDetails.duration_seconds === 0) && (
            <PipelineProcessor
              bookId={bookDetails.id}
              onSuccess={async () => {
                setShowInlineCompiler(false)
                await fetchBooks()
                await fetchBookDetails(bookDetails.id)
              }}
            />
          )}

          {/* Standard Dashboard Workspaces */}
          {bookDetails.duration_seconds > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              
              {/* Sticky Left Column: Video/Audio Player & Table of Contents Sidebar */}
              <div className="lg:col-span-4 space-y-6 lg:sticky lg:top-24 max-h-[calc(100vh-8rem)] overflow-y-auto pr-1">
                
                {/* Media Player Card */}
                <div className="border border-slate-800 bg-black aspect-video flex flex-col justify-center items-center overflow-hidden">
                  {bookDetails.media_type === 'local' && bookDetails.media_path ? (
                    <video
                      ref={videoPlayerRef}
                      src={`${getApiBaseUrl()}/storage/books/${bookDetails.id}/source_video.mp4`}
                      controls
                      className="w-full h-full object-contain"
                    />
                  ) : (
                    <div className="p-4 text-center">
                      <p className="font-mono text-xs text-fuchsia-400 tracking-wider mb-2 uppercase">// REMOTE AUDIO/VIDEO STREAMS LINKED PLAYER</p>
                      <p className="font-mono text-[9px] text-slate-500 mb-3 break-all max-w-xs mx-auto">
                        {bookDetails.source_url || 'No URL specified'}
                      </p>
                      <a
                        href={bookDetails.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-block border border-cyan-500 px-3 py-1.5 font-mono text-[9px] text-cyan-400"
                      >
                        [OPEN STREAMS ON WEB]
                      </a>
                    </div>
                  )}
                </div>

                {/* Monospace TOC Table of Contents Sidebar */}
                <div className="border border-slate-800 bg-[#0a0a0f] p-4 flex flex-col">
                  <div className="border-b border-slate-800 bg-slate-900/40 -mx-4 -mt-4 px-4 py-2 mb-3">
                    <h3 className="font-mono text-xs font-bold text-cyan-400 tracking-widest uppercase">// BOOK OUTLINE DIRECTORY (目录侧边栏)</h3>
                  </div>
                  
                  <div className="space-y-2 overflow-y-auto max-h-[40vh] custom-scrollbar">
                    {bookIndex && bookIndex.outline ? (
                      renderOutlineTree(bookIndex.outline)
                    ) : (
                      <p className="font-mono text-[10px] text-slate-500">// No outline index available.</p>
                    )}
                  </div>
                </div>
                
              </div>

              {/* Right Column: Full-Featured Monospace Markdown Reader Card */}
              <div className="lg:col-span-8 border border-slate-800 bg-[#0a0a0f] p-6 lg:p-8">
                <div className="border-b border-slate-800 bg-slate-900/20 -mx-6 -mt-6 lg:-mx-8 lg:-mt-8 px-6 lg:px-8 py-3 mb-6">
                  <h3 className="font-mono text-xs font-bold text-fuchsia-400 tracking-widest uppercase">// COMPILED INTELLECTUAL BOOK CONTENT (正文)</h3>
                </div>

                <div className="markdown-body font-mono text-xs text-slate-300 leading-relaxed space-y-4">
                  {bookContent ? (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm, remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                      components={markdownComponents as any}
                    >
                      {bookContent}
                    </ReactMarkdown>
                  ) : (
                    <p className="font-mono text-slate-500">// Loading book content from complete.md...</p>
                  )}
                </div>
              </div>

            </div>
          )}
        </div>
      )}
    </div>
  )
}
