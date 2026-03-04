import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { searchQuery } from '../api'
import type { UIChatMessage, Source } from '../types'
import KBSelector from '../components/KBSelector'
import Spinner from '../components/Spinner'
import ErrorMessage from '../components/ErrorMessage'

// ─── Componente badge score ──────────────────────────────────────────────────

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  let colorClass = 'bg-red-100 text-red-700'
  if (score >= 0.75) colorClass = 'bg-green-100 text-green-700'
  else if (score >= 0.5) colorClass = 'bg-yellow-100 text-yellow-700'
  else if (score >= 0.25) colorClass = 'bg-orange-100 text-orange-700'
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-semibold ${colorClass}`}>
      {pct}%
    </span>
  )
}

function shortFilename(path?: string): string {
  if (!path) return '—'
  return path.split('/').pop() ?? path
}

// ─── Pannello fonti collassabili ─────────────────────────────────────────────

function SourcesPanel({ sources }: { sources: Source[] }) {
  const [open, setOpen] = useState(false)
  if (!sources.length) return null
  return (
    <div className="mt-2 border-t border-blue-100 pt-2">
      <button
        onClick={() => setOpen(o => !o)}
        className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
      >
        <span>{open ? '▾' : '▸'}</span>
        {sources.length} {sources.length === 1 ? 'fonte' : 'fonti'}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {sources.map(src => (
            <div key={src.id} className="bg-white border border-gray-200 rounded p-2 text-xs shadow-sm">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">{src.kb_namespace}</span>
                <span className="text-gray-600 truncate" title={src.source_path}>
                  📄 {shortFilename(src.source_path)}
                </span>
                <ScoreBadge score={src.score} />
              </div>
              <p className="text-gray-700 leading-relaxed line-clamp-3">{src.excerpt}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Singola bolla chat ──────────────────────────────────────────────────────

function ChatBubble({ msg }: { msg: UIChatMessage }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-sm ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-sm'
            : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm'
        }`}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed">{msg.content}</p>
        ) : (
          <>
            <div className="text-sm leading-relaxed [&_strong]:font-semibold [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4 [&_table]:border-collapse [&_th]:border [&_th]:px-2 [&_th]:py-1 [&_td]:border [&_td]:px-2 [&_td]:py-1 [&_p]:mb-2 [&_p:last-child]:mb-0">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>
            {msg.sources && <SourcesPanel sources={msg.sources} />}
          </>
        )}
      </div>
    </div>
  )
}

// ─── Pagina principale ───────────────────────────────────────────────────────

export default function SearchPage() {
  const [messages, setMessages] = useState<UIChatMessage[]>([])
  const [input, setInput] = useState('')
  const [kb, setKb] = useState('')
  const [topK] = useState(5)
  const [searchMode] = useState<'vector' | 'fts' | 'hybrid'>('hybrid')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll al fondo dopo ogni nuovo messaggio
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg: UIChatMessage = { role: 'user', content: text }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setLoading(true)
    setError(null)

    // Prepara history per il backend (solo role+content, senza sources)
    const history = messages.map(m => ({ role: m.role, content: m.content }))

    try {
      const res = await searchQuery({
        query: text,
        kb: kb || undefined,
        top_k: topK,
        search_mode: searchMode,
        synthesize: true,
        history,
      })

      const assistantMsg: UIChatMessage = {
        role: 'assistant',
        content: res.answer,
        sources: res.sources,
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Errore sconosciuto')
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleReset = () => {
    setMessages([])
    setError(null)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Barra impostazioni compatta */}
      <div className="flex items-center gap-3 pb-3 border-b border-gray-200 mb-3 flex-shrink-0">
        <div className="w-44">
          <KBSelector value={kb} onChange={setKb} allOption="Tutte le KB" />
        </div>
        <span className="text-xs text-gray-400">hybrid search · top {topK}</span>
        {messages.length > 0 && (
          <button
            onClick={handleReset}
            className="ml-auto text-xs text-gray-400 hover:text-red-500 transition-colors"
          >
            ✕ Nuova conversazione
          </button>
        )}
      </div>

      {/* Area messaggi scrollabile */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-2 pr-1">
        {messages.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 select-none">
            <p className="text-5xl mb-3">💬</p>
            <p className="font-medium text-gray-500">Inizia una conversazione</p>
            <p className="text-sm mt-1">Fai una domanda sui documenti caricati</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatBubble key={i} msg={msg} />
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <Spinner />
            </div>
          </div>
        )}
        {error && <ErrorMessage message={error} />}
        <div ref={bottomRef} />
      </div>

      {/* Input fisso in fondo */}
      <div className="flex-shrink-0 pt-3 border-t border-gray-200">
        <div className="flex gap-2 items-end">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Scrivi una domanda… (Invio per inviare, Shift+Invio per andare a capo)"
            rows={2}
            disabled={loading}
            className="flex-1 resize-none rounded-xl border border-gray-300 px-3 py-2 text-sm
                       focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
                       disabled:bg-gray-50 disabled:text-gray-400"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-xl
                       hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed
                       transition-colors self-end"
          >
            Invia
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-1 text-right">
          Shift+Invio per andare a capo
        </p>
      </div>
    </div>
  )
}
