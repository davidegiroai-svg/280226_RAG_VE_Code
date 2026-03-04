import { useEffect, useState } from 'react'
import { listKbs } from '../api'
import type { KbInfo } from '../types'

interface KBSelectorProps {
  value: string
  onChange: (v: string) => void
  allOption?: string
  required?: boolean
}

export default function KBSelector({ value, onChange, allOption, required }: KBSelectorProps) {
  const [kbs, setKbs] = useState<KbInfo[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listKbs()
      .then(setKbs)
      .catch(() => setKbs([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      required={required}
      disabled={loading}
      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
    >
      {allOption && <option value="">{allOption}</option>}
      {loading && <option disabled>Caricamento...</option>}
      {kbs.map(kb => (
        <option key={kb.namespace} value={kb.namespace}>
          {kb.nome || kb.namespace}
        </option>
      ))}
      {!loading && kbs.length === 0 && !allOption && (
        <option value="" disabled>Nessuna KB disponibile</option>
      )}
    </select>
  )
}
