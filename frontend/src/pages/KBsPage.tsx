import { useEffect, useState } from 'react'
import { listKbs } from '../api'
import type { KbInfo } from '../types'
import Spinner from '../components/Spinner'
import ErrorMessage from '../components/ErrorMessage'

export default function KBsPage() {
  const [kbs, setKbs] = useState<KbInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    setError(null)
    listKbs()
      .then(setKbs)
      .catch(e => setError(e instanceof Error ? e.message : 'Errore caricamento KB'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">Knowledge Base</h2>
        <button onClick={load} className="text-sm text-blue-600 hover:underline">↺ Aggiorna</button>
      </div>

      {error && <ErrorMessage message={error} />}

      {loading ? (
        <Spinner />
      ) : kbs.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="text-4xl mb-2">🗂️</p>
          <p className="font-medium">Nessuna Knowledge Base trovata</p>
          <p className="text-sm mt-1">Carica dei documenti per creare la prima KB</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {kbs.map(kb => (
            <div key={kb.namespace} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="min-w-0">
                  <h3 className="font-semibold text-gray-800 truncate">
                    {kb.nome || kb.namespace}
                  </h3>
                  {kb.nome && (
                    <p className="text-xs text-gray-400 font-mono truncate">{kb.namespace}</p>
                  )}
                </div>
                <span className="text-xl ml-2">🗃️</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="bg-gray-50 rounded p-2">
                  <p className="text-xl font-bold text-blue-700">{kb.doc_count}</p>
                  <p className="text-xs text-gray-500">documenti</p>
                </div>
                <div className="bg-gray-50 rounded p-2">
                  <p className="text-xl font-bold text-blue-700">{kb.chunk_count}</p>
                  <p className="text-xs text-gray-500">chunk</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
