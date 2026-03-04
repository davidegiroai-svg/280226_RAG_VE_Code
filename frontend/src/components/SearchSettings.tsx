interface SearchSettingsProps {
  topK: number
  onTopKChange: (v: number) => void
  searchMode: 'vector' | 'fts' | 'hybrid'
  onSearchModeChange: (v: 'vector' | 'fts' | 'hybrid') => void
  synthesize: boolean
  onSynthesizeChange: (v: boolean) => void
}

const SEARCH_MODES: { value: 'vector' | 'fts' | 'hybrid'; label: string; desc: string }[] = [
  { value: 'hybrid', label: 'Ibrida', desc: 'Vettoriale + testo (consigliata)' },
  { value: 'vector', label: 'Vettoriale', desc: 'Ricerca per similarità semantica' },
  { value: 'fts', label: 'Testo', desc: 'Ricerca full-text classica' },
]

export default function SearchSettings({
  topK,
  onTopKChange,
  searchMode,
  onSearchModeChange,
  synthesize,
  onSynthesizeChange,
}: SearchSettingsProps) {
  return (
    <details className="group bg-white border border-gray-200 rounded-lg">
      <summary className="px-4 py-2 cursor-pointer text-sm text-gray-600 hover:text-gray-800 select-none list-none flex items-center justify-between">
        <span>⚙️ Impostazioni ricerca</span>
        <span className="text-gray-400 group-open:rotate-180 transition-transform">▾</span>
      </summary>

      <div className="px-4 pb-4 pt-2 border-t border-gray-100 grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* top_k */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Risultati: <span className="text-blue-600 font-bold">{topK}</span>
          </label>
          <input
            type="range"
            min={1}
            max={20}
            value={topK}
            onChange={e => onTopKChange(Number(e.target.value))}
            className="w-full accent-blue-600"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-0.5">
            <span>1</span><span>20</span>
          </div>
        </div>

        {/* search_mode */}
        <div>
          <p className="text-xs font-medium text-gray-700 mb-1">Modalità ricerca</p>
          <div className="space-y-1">
            {SEARCH_MODES.map(m => (
              <label key={m.value} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="search_mode"
                  value={m.value}
                  checked={searchMode === m.value}
                  onChange={() => onSearchModeChange(m.value)}
                  className="accent-blue-600"
                />
                <span className="text-xs text-gray-700">
                  <span className="font-medium">{m.label}</span>
                  <span className="text-gray-400"> — {m.desc}</span>
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* synthesize */}
        <div>
          <p className="text-xs font-medium text-gray-700 mb-1">Risposta IA</p>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={synthesize}
              onChange={e => onSynthesizeChange(e.target.checked)}
              className="w-4 h-4 accent-blue-600"
            />
            <span className="text-xs text-gray-700">
              Genera risposta con LLM
              <span className="block text-gray-400">Richiede Ollama attivo</span>
            </span>
          </label>
        </div>
      </div>
    </details>
  )
}
