import { useState } from 'react'
import { searchQuery } from '../api'
import type { QueryResponse } from '../types'
import SearchBar from '../components/SearchBar'
import SearchSettings from '../components/SearchSettings'
import SearchResult from '../components/SearchResult'
import KBSelector from '../components/KBSelector'
import Spinner from '../components/Spinner'
import ErrorMessage from '../components/ErrorMessage'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [kb, setKb] = useState('')
  const [topK, setTopK] = useState(5)
  const [searchMode, setSearchMode] = useState<'vector' | 'fts' | 'hybrid'>('hybrid')
  const [synthesize, setSynthesize] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await searchQuery({
        query: query.trim(),
        kb: kb || undefined,
        top_k: topK,
        search_mode: searchMode,
        synthesize,
      })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Errore sconosciuto')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="sm:w-48">
          <KBSelector value={kb} onChange={setKb} allOption="Tutte le KB" />
        </div>
        <div className="flex-1">
          <SearchBar
            value={query}
            onChange={setQuery}
            onSearch={handleSearch}
            loading={loading}
          />
        </div>
      </div>

      <SearchSettings
        topK={topK}
        onTopKChange={setTopK}
        searchMode={searchMode}
        onSearchModeChange={setSearchMode}
        synthesize={synthesize}
        onSynthesizeChange={setSynthesize}
      />

      {error && <ErrorMessage message={error} />}
      {loading && <Spinner />}

      {/* Risposta LLM */}
      {result && result.answer && result.answer !== 'Retrieval-only response.' && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs font-semibold text-blue-700 mb-1">Risposta IA</p>
          <p className="text-gray-800 text-sm leading-relaxed whitespace-pre-wrap">{result.answer}</p>
        </div>
      )}

      {/* Risultati */}
      {result && !loading && (
        <div>
          {result.sources.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <p className="text-4xl mb-2">🔍</p>
              <p className="font-medium">Nessun documento trovato</p>
              <p className="text-sm mt-1">Prova a cambiare la query o la modalità di ricerca</p>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-gray-500">
                {result.sources.length} risultat{result.sources.length === 1 ? 'o' : 'i'} trovati
              </p>
              {result.sources.map(source => (
                <SearchResult key={source.id} source={source} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
