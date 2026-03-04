import type { Source } from '../types'

interface SearchResultProps {
  source: Source
}

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  let colorClass = 'bg-red-100 text-red-700'
  if (score >= 0.75) colorClass = 'bg-green-100 text-green-700'
  else if (score >= 0.5) colorClass = 'bg-yellow-100 text-yellow-700'
  else if (score >= 0.25) colorClass = 'bg-orange-100 text-orange-700'

  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${colorClass}`}>
      {pct}%
    </span>
  )
}

function shortFilename(path?: string): string {
  if (!path) return '—'
  return path.split('/').pop() ?? path
}

export default function SearchResult({ source }: SearchResultProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded whitespace-nowrap">
            {source.kb_namespace}
          </span>
          <span className="text-xs text-gray-600 truncate" title={source.source_path}>
            📄 {shortFilename(source.source_path)}
          </span>
        </div>
        <ScoreBadge score={source.score} />
      </div>
      <p className="text-sm text-gray-700 leading-relaxed line-clamp-4">{source.excerpt}</p>
    </div>
  )
}
