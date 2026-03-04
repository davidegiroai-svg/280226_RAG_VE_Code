import { useEffect, useState } from 'react'
import { listDocuments } from '../api'
import type { DocumentInfo } from '../types'
import KBSelector from '../components/KBSelector'
import DocumentList from '../components/DocumentList'
import Spinner from '../components/Spinner'
import ErrorMessage from '../components/ErrorMessage'

export default function DocumentsPage() {
  const [kb, setKb] = useState('')
  const [showDeleted, setShowDeleted] = useState(false)
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = (kbFilter: string) => {
    setLoading(true)
    setError(null)
    listDocuments(kbFilter || undefined)
      .then(setDocuments)
      .catch(e => setError(e instanceof Error ? e.message : 'Errore caricamento documenti'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(kb) }, [kb])

  const visible = showDeleted ? documents : documents.filter(d => !d.is_deleted)

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="sm:w-56">
          <KBSelector value={kb} onChange={setKb} allOption="Tutte le KB" />
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={showDeleted}
            onChange={e => setShowDeleted(e.target.checked)}
            className="accent-blue-600"
          />
          Mostra eliminati
        </label>
        <button
          onClick={() => load(kb)}
          className="text-sm text-blue-600 hover:underline"
        >
          ↺ Aggiorna
        </button>
      </div>

      {error && <ErrorMessage message={error} />}

      {loading ? (
        <Spinner />
      ) : (
        <DocumentList documents={visible} />
      )}
    </div>
  )
}
