import React from 'react'

interface MilanoBook {
  id: string
  title: string
  author: string
}

interface AggregatorTabProps {
  books: MilanoBook[]
  selectedBookIdsForNote: string[]
  toggleBookSelectionForNote: (bookId: string) => void
  noteUserPrompt: string
  setNoteUserPrompt: (val: string) => void
  handleCompileCrossNote: (e: React.FormEvent) => Promise<void>
  isCompilingNote: boolean
}

export default function AggregatorTab({
  books,
  selectedBookIdsForNote,
  toggleBookSelectionForNote,
  noteUserPrompt,
  setNoteUserPrompt,
  handleCompileCrossNote,
  isCompilingNote
}: AggregatorTabProps) {
  return (
    <div className="mt-8 space-y-6 max-w-4xl mx-auto">
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
  )
}
