import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

interface MilanoNote {
  id: string
  book_ids: string[]
  content: string
  user_prompt?: string
  created_at: string
}

interface StudyNotesTabProps {
  allNotes: MilanoNote[]
  selectedNote: MilanoNote | null
  setSelectedNote: (note: MilanoNote | null) => void
  handleDeleteNote: (noteId: string, e?: React.MouseEvent) => Promise<void>
}

export default function StudyNotesTab({
  allNotes,
  selectedNote,
  setSelectedNote,
  handleDeleteNote
}: StudyNotesTabProps) {
  return (
    <div className="mt-8 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start max-w-6xl mx-auto">
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
  )
}
