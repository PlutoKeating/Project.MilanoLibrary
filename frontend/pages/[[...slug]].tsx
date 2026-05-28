import type { NextPage } from 'next'
import React, { useEffect, useState } from 'react'
import { HashRouter, Routes, Route, Navigate, Link, useNavigate, useLocation } from 'react-router-dom'

import { useLocalStorage } from '~/hooks/useLocalStorage'
import { getApiBaseUrl } from '~/lib/api'

import LibraryTab from '~/components/LibraryTab'
import AggregatorTab from '~/components/AggregatorTab'
import StudyNotesTab from '~/components/StudyNotesTab'
import SettingsTab from '~/components/SettingsTab'
import Login from '~/components/Login'

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
}

interface MilanoNote {
  id: string
  book_ids: string[]
  content: string
  user_prompt?: string
  created_at: string
}

function MainAppContent() {
  const navigate = useNavigate()
  const location = useLocation()

  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [loadingAuth, setLoadingAuth] = useState(true)

  const [books, setBooks] = useState<MilanoBook[]>([])
  const [allNotes, setAllNotes] = useState<MilanoNote[]>([])
  const [vaultPath, setVaultPath] = useState<string>('')
  const [vaultMessage, setVaultMessage] = useState('')
  const [selectedBookIdsForNote, setSelectedBookIdsForNote] = useState<string[]>([])
  const [noteUserPrompt, setNoteUserPrompt] = useState('')
  const [isCompilingNote, setIsCompilingNote] = useState(false)
  const [selectedNote, setSelectedNote] = useState<MilanoNote | null>(null)

  // Local keys / API configurations
  const [userKey, setUserKey] = useLocalStorage<string>('user-openai-apikey')
  const [userBaseUrl, setUserBaseUrl] = useLocalStorage<string>('user-openai-base-url')
  const [userModelName, setUserModelName] = useLocalStorage<string>('user-openai-model')
  const [backendBaseUrl, setBackendBaseUrl] = useLocalStorage<string>('backend-base-url')

  useEffect(() => {
    const token = window.localStorage.getItem('milano-auth-token')
    if (token === 'milano-auth-token') {
      setIsLoggedIn(true)
    }
    setLoadingAuth(false)
  }, [])

  const fetchVaultSettings = async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/books/settings/root`)
      if (res.ok) {
        const data = await res.json()
        setVaultPath(data.root_dir || '')
      }
    } catch (e) {
      console.error('Error fetching settings:', e)
    }
  }

  const handleSaveVault = async (targetPath: string) => {
    if (!targetPath || !targetPath.trim()) return
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
        setVaultMessage('SAVED & LOADED!')
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
    if (isLoggedIn) {
      fetchVaultSettings()
      fetchBooks()
      fetchNotes()
    }
  }, [isLoggedIn])

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

      await fetchBooks()
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
      } else {
        alert('DELETE FAILED')
      }
    } catch (e) {
      console.error(e)
    }
  }

  const handleCompileCrossNote = async (e: React.FormEvent) => {
    e.preventDefault()
    if (selectedBookIdsForNote.length === 0) {
      alert('SELECT AT LEAST ONE MILANOBOOK FOR SYNTHESIS')
      return
    }

    setIsCompilingNote(true)

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
        setNoteUserPrompt('')
        setSelectedBookIdsForNote([])
        await fetchNotes()
        setSelectedNote(newNote)
        navigate('/notes')
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

  if (loadingAuth) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center font-mono text-cyan-400">
        LOADING AUTH STATE...
      </div>
    )
  }

  if (!isLoggedIn) {
    return (
      <div className="w-full px-4 pt-10 pb-16 lg:px-0">
        <div className="mx-auto max-w-6xl">
          <h1 className="text-center font-mono text-3xl font-bold tracking-widest text-cyan-400 sm:text-5xl">MILANO LIBRARY</h1>
          <p className="mt-2 text-center font-mono text-xs tracking-widest text-fuchsia-400">
            DATABASE-LESS VIDEO VAULT & RECOMPOSITION COMPILER
          </p>
          <Login
            onLoginSuccess={() => setIsLoggedIn(true)}
            backendBaseUrl={backendBaseUrl || 'http://localhost:8000'}
            setBackendBaseUrl={setBackendBaseUrl}
          />
        </div>
      </div>
    )
  }

  const activeTab = location.pathname

  return (
    <div className="w-full px-4 pt-10 pb-16 lg:px-0">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="text-center sm:text-left">
            <h1 className="font-mono text-3xl font-bold tracking-widest text-cyan-400 sm:text-5xl">MILANO LIBRARY</h1>
            <p className="mt-2 font-mono text-xs tracking-widest text-fuchsia-400">
              DATABASE-LESS VIDEO VAULT & RECOMPOSITION COMPILER
            </p>
          </div>
          <button
            onClick={() => {
              window.localStorage.removeItem('milano-auth-token')
              setIsLoggedIn(false)
            }}
            className="border border-slate-800 hover:border-red-500 hover:text-red-400 px-3 py-1 font-mono text-[10px] text-slate-500 uppercase transition-colors"
          >
            [ LOGOUT ]
          </button>
        </div>

        {/* 4 Main Tabs Nav */}
        <div className="mt-10 flex border-b border-slate-800">
          <Link
            to="/library"
            className={`px-6 py-3 font-mono text-xs tracking-wider uppercase border-t border-l border-r border-transparent ${
              activeTab === '/library' || activeTab === '/' ? 'text-cyan-400 border-slate-800 bg-[#0c0c14]/40 font-bold border-b-2 border-b-cyan-400' : 'text-slate-400 hover:text-cyan-200'
            }`}
          >
            [LIBRARY // 视频知识库]
          </Link>
          <Link
            to="/aggregator"
            className={`px-6 py-3 font-mono text-xs tracking-wider uppercase border-t border-l border-r border-transparent ${
              activeTab === '/aggregator' ? 'text-cyan-400 border-slate-800 bg-[#0c0c14]/40 font-bold border-b-2 border-b-cyan-400' : 'text-slate-400 hover:text-cyan-200'
            }`}
          >
            [AGGREGATOR // 多书整合]
          </Link>
          <Link
            to="/notes"
            className={`px-6 py-3 font-mono text-xs tracking-wider uppercase border-t border-l border-r border-transparent ${
              activeTab === '/notes' ? 'text-cyan-400 border-slate-800 bg-[#0c0c14]/40 font-bold border-b-2 border-b-cyan-400' : 'text-slate-400 hover:text-cyan-200'
            }`}
          >
            [STUDY NOTES // 智能笔记]
          </Link>
          <Link
            to="/settings"
            className={`px-6 py-3 font-mono text-xs tracking-wider uppercase border-t border-l border-r border-transparent ${
              activeTab === '/settings' ? 'text-cyan-400 border-slate-800 bg-[#0c0c14]/40 font-bold border-b-2 border-b-cyan-400' : 'text-slate-400 hover:text-cyan-200'
            }`}
          >
            [SETTINGS // 设置]
          </Link>
        </div>

        {/* Routes Content */}
        <Routes>
          <Route path="/" element={<Navigate to="/library" replace />} />
          <Route path="/library" element={
            <LibraryTab
              books={books}
              fetchBooks={fetchBooks}
              vaultPath={vaultPath}
              handleDirectCreateBook={handleDirectCreateBook}
              handleDeleteBook={handleDeleteBook}
            />
          } />
          <Route path="/aggregator" element={
            <AggregatorTab
              books={books}
              selectedBookIdsForNote={selectedBookIdsForNote}
              toggleBookSelectionForNote={toggleBookSelectionForNote}
              noteUserPrompt={noteUserPrompt}
              setNoteUserPrompt={setNoteUserPrompt}
              handleCompileCrossNote={handleCompileCrossNote}
              isCompilingNote={isCompilingNote}
            />
          } />
          <Route path="/notes" element={
            <StudyNotesTab
              allNotes={allNotes}
              selectedNote={selectedNote}
              setSelectedNote={setSelectedNote}
              handleDeleteNote={handleDeleteNote}
            />
          } />
          <Route path="/settings" element={
            <SettingsTab
              vaultPath={vaultPath}
              handleSaveVault={handleSaveVault}
              vaultMessage={vaultMessage}
              userKey={userKey}
              setUserKey={setUserKey}
              userBaseUrl={userBaseUrl}
              setUserBaseUrl={setUserBaseUrl}
              userModelName={userModelName}
              setUserModelName={setUserModelName}
              backendBaseUrl={backendBaseUrl}
              setBackendBaseUrl={setBackendBaseUrl}
            />
          } />
        </Routes>
      </div>
    </div>
  )
}

export const Home: NextPage = () => {
  const [isMounted, setIsMounted] = useState(false)
  useEffect(() => {
    setIsMounted(true)
  }, [])

  if (!isMounted) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0a0a0f] font-mono text-cyan-400">
        LOADING SYSTEM CORE...
      </div>
    )
  }

  return (
    <HashRouter>
      <MainAppContent />
    </HashRouter>
  )
}

export default Home
