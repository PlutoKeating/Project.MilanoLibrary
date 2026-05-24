import { zodResolver } from '@hookform/resolvers/zod'
import type { NextPage } from 'next'
import { useRouter } from 'next/router'
import React, { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import { SubmitHandler, useForm } from 'react-hook-form'
import useFormPersist from 'react-hook-form-persist'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

import { UserKeyInput } from '~/components/UserKeyInput'
import { FileExplorer } from '~/components/FileExplorer'
import { PipelineProcessor } from '~/components/PipelineProcessor'
import { TimelineProgress } from '~/components/TimelineProgress'
import { useClearCache } from '~/hooks/useClearCache'
import { useLocalStorage } from '~/hooks/useLocalStorage'
import { useModelManager } from '~/hooks/useModelManager'
import { TaskStatus } from '~/hooks/useSummarize'
import { VideoService } from '~/lib/types'
import { DEFAULT_LANGUAGE } from '~/utils/constants/language'
import { extractPage, extractUrl } from '~/utils/extractUrl'
import { getVideoIdFromUrl } from '~/utils/getVideoIdFromUrl'
import { VideoConfigSchema, videoConfigSchema } from '~/utils/schemas/video'
import { getApiBaseUrl } from '~/lib/api'

// --- Types ---
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

interface MilanoNote {
  id: string
  book_ids: string[]
  content: string
  user_prompt?: string
  created_at: string
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

export const Home: NextPage = () => {
  const router = useRouter()
  const urlState = router.query.slug
  const searchParams = useMemo(() => {
    const [, queryString = ''] = router.asPath.split('?')
    return new URLSearchParams(queryString)
  }, [router.asPath])

  // --- UI Layout state ---
  const [activeTab, setActiveTab] = useState<'library' | 'aggregator' | 'notes'>('library')
  const [books, setBooks] = useState<MilanoBook[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [bookDetails, setBookDetails] = useState<MilanoBook | null>(null)
  const [bookContent, setBookContent] = useState<string>('')
  const [bookIndex, setBookIndex] = useState<any>(null)
  const [activeDetailTab, setActiveDetailTab] = useState<'timeline' | 'stuff' | 'graph'>('timeline')
  
  // Vault Settings states
  const [vaultPath, setVaultPath] = useState<string>('')
  const [tempVaultPath, setTempVaultPath] = useState<string>('')
  const [isSavingVault, setIsSavingVault] = useState(false)
  const [vaultMessage, setVaultMessage] = useState('')
  const [showExplorer, setShowExplorer] = useState(false)

  // Inline Reprocessing toggle in book detail
  const [showInlineCompiler, setShowInlineCompiler] = useState(false)
  const [isRecompiling, setIsRecompiling] = useState(false)

  // Notes Aggregator States
  const [selectedBookIdsForNote, setSelectedBookIdsForNote] = useState<string[]>([])
  const [noteUserPrompt, setNoteUserPrompt] = useState('')
  const [isCompilingNote, setIsCompilingNote] = useState(false)
  const [compiledNoteResult, setCompiledNoteResult] = useState<MilanoNote | null>(null)
  const [allNotes, setAllNotes] = useState<MilanoNote[]>([])
  const [selectedNote, setSelectedNote] = useState<MilanoNote | null>(null)

  // Player ref
  const videoPlayerRef = useRef<HTMLVideoElement>(null)

  // Global Configuration Keys
  const [userKey, setUserKey] = useLocalStorage<string>('user-openai-apikey')
  const [userBaseUrl, setUserBaseUrl] = useLocalStorage<string>('user-openai-base-url')
  const [userModelName, setUserModelName] = useLocalStorage<string>('user-openai-model')
  const [backendBaseUrl, setBackendBaseUrl] = useLocalStorage<string>('backend-base-url')

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

  // --- Fetch Operations ---
  const fetchVaultSettings = async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/books/settings/root`)
      if (res.ok) {
        const data = await res.json()
        setVaultPath(data.root_dir || '')
        setTempVaultPath(data.root_dir || '')
      }
    } catch (e) {
      console.error('Error fetching settings:', e)
    }
  }

  const handleSaveVault = async (targetPath: string) => {
    if (!targetPath || !targetPath.trim()) return
    setIsSavingVault(true)
    setVaultMessage('')
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/books/settings/root`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: targetPath })
      })
      if (res.ok) {
        const data = await res.json()
        setVaultPath(data.root_dir)
        setTempVaultPath(data.root_dir)
        setVaultMessage('SAVED & LOADED!')
        setBookDetails(null)
        await fetchBooks()
        await fetchNotes()
        setTimeout(() => setVaultMessage(''), 3000)
      } else {
        const err = await res.json()
        alert(`SAVE FAILED: ${err.detail || 'Path is invalid'}`)
      }
    } catch (e) {
      console.error(e)
      alert('FAILED TO CONNECT TO SETTINGS API')
    } finally {
      setIsSavingVault(false)
    }
  }

  const fetchBooks = async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/books`)
      if (res.ok) {
        const data = await res.json()
        setBooks(data.books || [])
      }
    } catch (e) {
      console.error('Error fetching books:', e)
    }
  }

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

  const fetchNotes = async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/notes`)
      if (res.ok) {
        const data = await res.json()
        setAllNotes(data.notes || [])
      }
    } catch (e) {
      console.error('Error fetching notes:', e)
    }
  }

  useEffect(() => {
    fetchVaultSettings()
    fetchBooks()
    fetchNotes()
  }, [])

  const handleDirectCreateBook = async () => {
    try {
      const pad = (n: number) => String(n).padStart(2, '0')
      const now = new Date()
      const formattedDate = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
      const formattedTime = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
      const defaultTitle = `Untitled Vault ${formattedDate} ${formattedTime}`

      const createRes = await fetch(`${getApiBaseUrl()}/api/books`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: defaultTitle,
          author: 'Unknown',
          description: null
        })
      })

      if (!createRes.ok) {
        throw new Error('FAILED TO INITIALIZE BOOK')
      }

      const newBook = await createRes.json()
      await fetchBooks()
      handleOpenBookTerminal(newBook.id)
    } catch (err) {
      console.error(err)
      alert('ERROR CREATING NEW BOOK')
    }
  }

  const handleDeleteBook = async (bookId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    if (!confirm('CONFIRM PERMANENT DELETION OF MILANOBOOK DIR AND ENTIRE ATTACHED JSON/MEDIA ASSETS?')) return

    try {
      const res = await fetch(`${getApiBaseUrl()}/api/books/${bookId}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        await fetchBooks()
        if (bookDetails?.id === bookId) {
          setBookDetails(null)
        }
      } else {
        alert('DELETE FAILED')
      }
    } catch (e) {
      console.error(e)
    }
  }

  const handleOpenBookTerminal = async (bookId: string) => {
    setBookDetails(null)
    setShowInlineCompiler(false)
    await fetchBookDetails(bookId)
  }

  const handleSeekVideo = (seconds: number) => {
    if (videoPlayerRef.current) {
      videoPlayerRef.current.currentTime = seconds
      videoPlayerRef.current.play().catch(() => {})
    }
  }

  // --- Notes functions ---
  const handleCompileCrossNote = async (e: React.FormEvent) => {
    e.preventDefault()
    if (selectedBookIdsForNote.length === 0) {
      alert('SELECT AT LEAST ONE MILANOBOOK FOR SYNTHESIS')
      return
    }

    setIsCompilingNote(true)
    setCompiledNoteResult(null)

    try {
      const res = await fetch(`${getApiBaseUrl()}/api/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          book_ids: selectedBookIdsForNote,
          user_prompt: noteUserPrompt || null
        })
      })

      if (res.ok) {
        const newNote = await res.json()
        setCompiledNoteResult(newNote)
        setNoteUserPrompt('')
        setSelectedBookIdsForNote([])
        await fetchNotes()
        setSelectedNote(newNote)
        setActiveTab('notes')
      } else {
        const err = await res.text()
        alert(`COMPILATION ERROR: ${err}`)
      }
    } catch (e) {
      console.error(e)
      alert('LLM NOTE SYNTHESIS TIMED OUT')
    } finally {
      setIsCompilingNote(false)
    }
  }

  const handleDeleteNote = async (noteId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    if (!confirm('CONFIRM DELETION OF THIS RESEARCH NOTE?')) return

    try {
      const res = await fetch(`${getApiBaseUrl()}/api/notes/${noteId}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        await fetchNotes()
        if (selectedNote?.id === noteId) {
          setSelectedNote(null)
        }
      }
    } catch (e) {
      console.error(e)
    }
  }

  const toggleBookSelectionForNote = (bookId: string) => {
    if (selectedBookIdsForNote.includes(bookId)) {
      setSelectedBookIdsForNote(selectedBookIdsForNote.filter(id => id !== bookId))
    } else {
      setSelectedBookIdsForNote([...selectedBookIdsForNote, bookId])
    }
  }

  const handleApiKeyChange = (e: any) => setUserKey(e.target.value)
  const handleBaseUrlChange = (e: any) => setUserBaseUrl(e.target.value)
  const handleModelNameChange = (e: any) => setUserModelName(e.target.value)
  const handleBackendBaseUrlChange = (e: any) => setBackendBaseUrl(e.target.value)

  const filteredBooks = useMemo(() => {
    return books.filter(b => 
      b.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      b.author.toLowerCase().includes(searchQuery.toLowerCase())
    )
  }, [books, searchQuery])

  return (
    <div className="w-full px-4 pt-10 pb-16 lg:px-0">
      <div className="mx-auto max-w-6xl">
        <h1 className="text-center font-mono text-3xl font-bold tracking-widest text-cyan-400 sm:text-5xl">MILANO LIBRARY</h1>
        <p className="mt-2 text-center font-mono text-xs tracking-widest text-fuchsia-400">
          DATABASE-LESS VIDEO VAULT & RECOMPOSITION COMPILER
        </p>

        {/* Global Settings with Vault Directory Input */}
        <div className="mx-auto max-w-3xl border border-slate-800 bg-[#0a0a0f] p-4 mt-6">
          <div className="flex flex-col md:flex-row gap-4 items-end">
            <div className="flex-1 w-full">
              <label className="block font-mono text-[10px] font-bold text-fuchsia-400 uppercase tracking-widest mb-1">
                // OBSIDIAN ROOT VAULT PATH (本地书籍根目录)
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  readOnly
                  placeholder="选择磁盘上的书籍根目录绝对路径..."
                  value={vaultPath}
                  className="flex-1 border border-slate-800 bg-slate-950/60 px-3 py-2 font-mono text-xs text-cyan-200 outline-none select-all cursor-not-allowed"
                />
                <button
                  type="button"
                  onClick={() => setShowExplorer(!showExplorer)}
                  className="border border-slate-700 hover:border-cyan-500 hover:bg-cyan-500/10 px-4 py-2 font-mono text-xs text-cyan-400 uppercase font-bold transition-colors"
                >
                  {showExplorer ? 'HIDE BROWSE' : 'BROWSE...'}
                </button>
              </div>
            </div>
          </div>
          {showExplorer && (
            <div className="mt-4">
              <FileExplorer
                backendUrl={getApiBaseUrl()}
                initialPath={vaultPath}
                onSelect={(selectedPath) => {
                  handleSaveVault(selectedPath)
                  setShowExplorer(false)
                }}
                onClose={() => setShowExplorer(false)}
              />
            </div>
          )}
          {vaultMessage && (
            <p className="mt-2 font-mono text-[10px] text-cyan-400 text-right uppercase tracking-wider font-bold">
              {vaultMessage}
            </p>
          )}
        </div>

        {/* Global Key Config */}
        <div className="mx-auto max-w-3xl">
          <UserKeyInput
            value={userKey}
            onChange={handleApiKeyChange}
            baseUrl={userBaseUrl}
            onBaseUrlChange={handleBaseUrlChange}
            modelName={userModelName}
            onModelNameChange={handleModelNameChange}
            backendBaseUrl={backendBaseUrl}
            onBackendBaseUrlChange={handleBackendBaseUrlChange}
          />
        </div>

        {/* 3 Main Tabs Nav */}
        <div className="mt-10 flex border-b border-slate-800">
          <button
            onClick={() => { setActiveTab('library'); setBookDetails(null); }}
            className={`px-6 py-3 font-mono text-xs tracking-wider uppercase border-t border-l border-r border-transparent ${
              activeTab === 'library' ? 'text-cyan-400 border-slate-800 bg-[#0c0c14]/40 font-bold border-b-2 border-b-cyan-400' : 'text-slate-400 hover:text-cyan-200'
            }`}
          >
            [LIBRARY // 视频知识库]
          </button>
          <button
            onClick={() => { setActiveTab('aggregator'); setBookDetails(null); }}
            className={`px-6 py-3 font-mono text-xs tracking-wider uppercase border-t border-l border-r border-transparent ${
              activeTab === 'aggregator' ? 'text-cyan-400 border-slate-800 bg-[#0c0c14]/40 font-bold border-b-2 border-b-cyan-400' : 'text-slate-400 hover:text-cyan-200'
            }`}
          >
            [AGGREGATOR // 多书整合]
          </button>
          <button
            onClick={() => { setActiveTab('notes'); setBookDetails(null); }}
            className={`px-6 py-3 font-mono text-xs tracking-wider uppercase border-t border-l border-r border-transparent ${
              activeTab === 'notes' ? 'text-cyan-400 border-slate-800 bg-[#0c0c14]/40 font-bold border-b-2 border-b-cyan-400' : 'text-slate-400 hover:text-cyan-200'
            }`}
          >
            [STUDY NOTES // 智能笔记]
          </button>
        </div>

        {/* --- LIBRARY TAB --- */}
        {activeTab === 'library' && !bookDetails && (
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
                          onClick={(e) => { e.stopPropagation(); handleDeleteBook(book.id); }}
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
        {bookDetails && activeTab === 'library' && (
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
                  onClick={() => handleDeleteBook(bookDetails.id)}
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

        {/* --- AGGREGATOR TAB --- */}
        {activeTab === 'aggregator' && (
          <div className="mt-8 space-y-6 max-w-4xl">
            <h3 className="font-mono text-xs font-bold text-fuchsia-400 uppercase tracking-widest">
              // KNOWLEDGE VAULTS CROSS-COMPILER / 跨多书整合提炼控制台
            </h3>

            <form onSubmit={handleCompileCrossNote} className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
              {/* Checkboxes column */}
              <div className="md:col-span-5 border border-slate-800 bg-[#0a0a0f] p-4">
                <h4 className="font-mono text-xs font-bold text-cyan-400 uppercase mb-4 border-b border-slate-900 pb-2">
                  选择源 MilanoBooks
                </h4>
                {books.length === 0 ? (
                  <p className="font-mono text-[10px] text-slate-500">// No books found under active root dir</p>
                ) : (
                  <div className="space-y-2 max-h-80 overflow-y-auto">
                    {books.map(b => {
                      const isSelected = selectedBookIdsForNote.includes(b.id)
                      return (
                        <div
                          key={b.id}
                          onClick={() => toggleBookSelectionForNote(b.id)}
                          className={`p-2.5 border cursor-pointer font-mono text-xs flex justify-between items-center transition-colors ${
                            isSelected ? 'border-cyan-500 bg-cyan-950/20 text-cyan-300' : 'border-slate-900 hover:border-slate-800 text-slate-400'
                          }`}
                        >
                          <span className="line-clamp-1">{b.title}</span>
                          <span className="shrink-0 text-[10px] px-1 font-mono font-bold">
                            {isSelected ? '[X]' : '[ ]'}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Directives prompts */}
              <div className="md:col-span-7 space-y-4">
                <div className="flex flex-col">
                  <label className="font-mono text-xs font-bold text-cyan-400 uppercase mb-2">
                    输入综合性编排指令 (Study Notes Prompt)
                  </label>
                  <textarea
                    placeholder="输入交叉提炼指示... (例如：重点分析这几个视频在XX框架技术选型上的共同点、相异点及未来推导逻辑)"
                    value={noteUserPrompt}
                    onChange={e => setNoteUserPrompt(e.target.value)}
                    rows={6}
                    className="w-full border border-slate-800 bg-slate-900/30 p-3 font-mono text-xs text-cyan-100 placeholder-slate-600 outline-none focus:border-cyan-500"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isCompilingNote || selectedBookIdsForNote.length === 0}
                  className="w-full border border-cyan-500 hover:bg-cyan-500/10 disabled:opacity-40 disabled:cursor-not-allowed py-3 font-mono text-xs text-cyan-400 uppercase tracking-widest font-bold"
                >
                  {isCompilingNote ? 'COMPILING INTEGRATED STUDY GUIDE... (请耐心等候大模型编排)' : '[COMPILE COLLECTIVE NOTE // 启动跨领域提炼]'}
                </button>

                {isCompilingNote && (
                  <div className="border border-dashed border-cyan-500/50 p-4 bg-slate-950 text-center font-mono text-xs text-cyan-400 animate-pulse">
                    🚀 大模型正在抓取这 {selectedBookIdsForNote.length} 本米兰之书的技术大纲、技术柜并融会贯通中，请勿关闭本页面...
                  </div>
                )}
              </div>
            </form>
          </div>
        )}

        {/* --- STUDY NOTES TAB --- */}
        {activeTab === 'notes' && (
          <div className="mt-8 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Notes List Column */}
            <div className="lg:col-span-4 border border-slate-800 bg-[#0a0a0f] p-4 space-y-4">
              <h4 className="font-mono text-xs font-bold text-cyan-400 uppercase tracking-widest border-b border-slate-900 pb-2">// NOTES DIRECTORY (.NOTES/)</h4>
              {allNotes.length === 0 ? (
                <p className="font-mono text-[10px] text-slate-500">// No notes compiled yet inside this root vault</p>
              ) : (
                <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                  {allNotes.map(note => {
                    const isSelected = selectedNote?.id === note.id
                    return (
                      <div
                        key={note.id}
                        onClick={() => setSelectedNote(note)}
                        className={`p-3 border cursor-pointer flex flex-col justify-between transition-all ${
                          isSelected ? 'border-cyan-500 bg-cyan-950/10' : 'border-slate-900 hover:border-slate-800'
                        }`}
                      >
                        <span className="font-mono text-xs font-bold text-cyan-100 line-clamp-2">
                          Note: {new Date(note.created_at).toLocaleString()}
                        </span>
                        <span className="mt-1 font-mono text-[10px] text-slate-500 uppercase">
                          Source Books count: {note.book_ids.length}
                        </span>
                        <div className="mt-3 flex justify-between items-center text-[10px] font-mono">
                          <span className="text-cyan-400 hover:underline">[OPEN NOTE]</span>
                          <button
                            onClick={(e) => handleDeleteNote(note.id, e)}
                            className="text-slate-500 hover:text-red-400"
                          >
                            [DELETE]
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Note Viewer Column */}
            <div className="lg:col-span-8 border border-slate-800">
              <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-2 flex items-center justify-between">
                <h4 className="font-mono text-xs font-bold text-cyan-400 uppercase tracking-widest">// NOTE READER</h4>
                {selectedNote && (
                  <button
                    onClick={() => navigator.clipboard.writeText(selectedNote.content)}
                    className="font-mono text-[10px] text-fuchsia-400 hover:text-fuchsia-300"
                  >
                    [COPY MARKDOWN]
                  </button>
                )}
              </div>
              <div className="p-6">
                {!selectedNote ? (
                  <div className="p-12 text-center font-mono text-xs text-slate-500 border border-dashed border-slate-900">
                    // CHOOSE A COMPILED STUDY GUIDE FROM THE SIDEBAR ON THE LEFT OR TRIGGER COMPILATION DIRECTLY UNDER THE [AGGREGATOR] WORKSPACE
                  </div>
                ) : (
                  <div className="markdown-body p-2 font-mono max-h-[700px] overflow-y-auto leading-relaxed">
                    {selectedNote.user_prompt && (
                      <div className="mb-6 border border-slate-900 bg-slate-950 p-3 text-[11px] text-fuchsia-400">
                        <span className="font-bold">AGGREGATION INSTRUCTION DIRECTIVE:</span> "{selectedNote.user_prompt}"
                      </div>
                    )}
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm, remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                      components={{
                        h1: ({ children, ...props }: any) => <h1 className="font-mono font-bold text-cyan-400 mb-4 pb-2 border-b border-slate-800" {...props}>{children}</h1>,
                        h2: ({ children, ...props }: any) => <h2 className="font-mono font-bold text-cyan-400 mb-4 pb-2 border-b border-slate-800" {...props}>{children}</h2>,
                        h3: ({ children, ...props }: any) => <h3 className="font-mono font-bold text-cyan-400 mb-3 pb-1 border-b border-slate-800/50" {...props}>{children}</h3>,
                        h4: ({ children, ...props }: any) => <h4 className="font-mono font-bold text-fuchsia-400 mb-2" {...props}>{children}</h4>,
                        table: ({ children, ...props }: any) => <table className="border-collapse border border-slate-800 w-full text-xs font-mono text-left my-4" {...props}>{children}</table>,
                        th: ({ children, ...props }: any) => <th className="border border-slate-800 bg-slate-900/30 p-2 font-bold" {...props}>{children}</th>,
                        td: ({ children, ...props }: any) => <td className="border border-slate-800 p-2" {...props}>{children}</td>,
                        pre: ({ children, ...props }: any) => <pre className="border border-slate-800 bg-black/60 p-4 overflow-x-auto text-xs leading-normal" {...props}>{children}</pre>
                      }}
                    >
                      {selectedNote.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}

export default Home
