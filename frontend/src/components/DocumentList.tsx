import type { DocumentInfo } from '../types'

interface DocumentListProps {
  documents: DocumentInfo[]
}

function StatusBadge({ status, isDeleted }: { status?: string; isDeleted: boolean }) {
  if (isDeleted) {
    return <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500">eliminato</span>
  }
  const s = status || 'indexed'
  if (s === 'indexed') return <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">indicizzato</span>
  if (s === 'error') return <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">errore</span>
  return <span className="px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-700">{s}</span>
}

function shortFilename(path?: string): string {
  if (!path) return '—'
  return path.split('/').pop() ?? path
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '—'
  try {
    return new Date(dateStr).toLocaleDateString('it-IT', {
      day: '2-digit', month: '2-digit', year: 'numeric'
    })
  } catch {
    return dateStr
  }
}

export default function DocumentList({ documents }: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <p className="text-4xl mb-2">📂</p>
        <p className="font-medium">Nessun documento trovato</p>
        <p className="text-sm mt-1">Carica dei file dalla pagina Upload</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
            <th className="pb-2 pr-4">File</th>
            <th className="pb-2 pr-4">Knowledge Base</th>
            <th className="pb-2 pr-4">Stato</th>
            <th className="pb-2">Data</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {documents.map(doc => (
            <tr key={doc.id} className={`hover:bg-gray-50 ${doc.is_deleted ? 'opacity-50' : ''}`}>
              <td className="py-2 pr-4">
                <div className="font-medium text-gray-800 truncate max-w-xs" title={doc.source_path}>
                  {doc.titolo || shortFilename(doc.source_path)}
                </div>
                {doc.titolo && (
                  <div className="text-xs text-gray-400 truncate">{shortFilename(doc.source_path)}</div>
                )}
              </td>
              <td className="py-2 pr-4">
                <span className="text-xs font-medium text-gray-600 bg-gray-100 px-2 py-0.5 rounded">
                  {doc.kb_namespace}
                </span>
              </td>
              <td className="py-2 pr-4">
                <StatusBadge status={doc.ingest_status} isDeleted={doc.is_deleted} />
              </td>
              <td className="py-2 text-gray-500 whitespace-nowrap">
                {formatDate(doc.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
