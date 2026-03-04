import { useRef, useState } from 'react'

const ALLOWED_EXTENSIONS = ['.pdf', '.txt', '.md', '.csv', '.json']
const MAX_SIZE_MB = 50

interface FileUploadProps {
  files: File[]
  onChange: (files: File[]) => void
}

function validateFile(file: File): string | null {
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `Tipo non supportato: ${file.name} (accettati: ${ALLOWED_EXTENSIONS.join(', ')})`
  }
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    return `File troppo grande: ${file.name} (max ${MAX_SIZE_MB}MB)`
  }
  return null
}

export default function FileUpload({ files, onChange }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [validationErrors, setValidationErrors] = useState<string[]>([])

  const processFiles = (newFiles: FileList | null) => {
    if (!newFiles) return
    const errors: string[] = []
    const valid: File[] = []
    Array.from(newFiles).forEach(f => {
      const err = validateFile(f)
      if (err) errors.push(err)
      else valid.push(f)
    })
    setValidationErrors(errors)
    if (valid.length > 0) {
      const existing = files.map(f => f.name)
      const unique = valid.filter(f => !existing.includes(f.name))
      onChange([...files, ...unique])
    }
  }

  const removeFile = (name: string) => {
    onChange(files.filter(f => f.name !== name))
  }

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); processFiles(e.dataTransfer.files) }}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400 bg-gray-50'
        }`}
      >
        <p className="text-3xl mb-2">📁</p>
        <p className="text-sm font-medium text-gray-700">Trascina i file qui o clicca per selezionare</p>
        <p className="text-xs text-gray-500 mt-1">
          Formati: {ALLOWED_EXTENSIONS.join(', ')} — Max {MAX_SIZE_MB}MB per file
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ALLOWED_EXTENSIONS.join(',')}
          className="hidden"
          onChange={e => processFiles(e.target.files)}
        />
      </div>

      {/* Errori di validazione */}
      {validationErrors.map((err, i) => (
        <div key={i} className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          ⚠️ {err}
        </div>
      ))}

      {/* Lista file selezionati */}
      {files.length > 0 && (
        <ul className="space-y-1">
          {files.map(f => (
            <li key={f.name} className="flex items-center justify-between text-sm bg-white border border-gray-200 rounded px-3 py-2">
              <span className="flex items-center gap-2 truncate">
                <span>📄</span>
                <span className="truncate">{f.name}</span>
                <span className="text-gray-400 whitespace-nowrap">
                  ({(f.size / 1024 / 1024).toFixed(1)}MB)
                </span>
              </span>
              <button
                onClick={() => removeFile(f.name)}
                className="text-gray-400 hover:text-red-500 ml-2 flex-shrink-0"
                title="Rimuovi"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
