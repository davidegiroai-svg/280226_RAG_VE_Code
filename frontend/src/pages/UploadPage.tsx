import { useState } from 'react'
import { uploadFiles } from '../api'
import FileUpload from '../components/FileUpload'
import KBSelector from '../components/KBSelector'

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error'

export default function UploadPage() {
  const [kb, setKb] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [status, setStatus] = useState<UploadStatus>('idle')
  const [message, setMessage] = useState('')

  const handleUpload = async () => {
    if (!kb) { setMessage('Selezionare una Knowledge Base'); setStatus('error'); return }
    if (files.length === 0) { setMessage('Nessun file selezionato'); setStatus('error'); return }

    setStatus('uploading')
    setMessage('')
    try {
      const res = await uploadFiles(kb, files)
      setMessage(`Upload completato: ${res.files.join(', ')}`)
      setStatus('success')
      setFiles([])
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Errore durante l\'upload')
      setStatus('error')
    }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <h2 className="text-lg font-semibold text-gray-800">Carica documenti</h2>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Knowledge Base <span className="text-red-500">*</span>
        </label>
        <KBSelector value={kb} onChange={setKb} required />
      </div>

      <FileUpload files={files} onChange={setFiles} />

      <button
        onClick={handleUpload}
        disabled={status === 'uploading' || files.length === 0 || !kb}
        className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {status === 'uploading' ? (
          <span className="flex items-center justify-center gap-2">
            <span className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Caricamento in corso...
          </span>
        ) : `Carica ${files.length > 0 ? files.length + ' file' : 'file'}`}
      </button>

      {/* Messaggio esito */}
      {message && (
        <div className={`p-3 rounded-lg text-sm border ${
          status === 'success'
            ? 'bg-green-50 border-green-200 text-green-700'
            : 'bg-red-50 border-red-200 text-red-700'
        }`}>
          {status === 'success' ? '✅ ' : '⚠️ '}{message}
        </div>
      )}

      <p className="text-xs text-gray-400">
        I file vengono salvati nella inbox della KB selezionata e indicizzati automaticamente dal watcher.
      </p>
    </div>
  )
}
