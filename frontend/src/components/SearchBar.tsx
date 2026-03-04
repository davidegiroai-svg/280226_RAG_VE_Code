interface SearchBarProps {
  value: string
  onChange: (v: string) => void
  onSearch: () => void
  loading: boolean
}

export default function SearchBar({ value, onChange, onSearch, loading }: SearchBarProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading) onSearch()
  }

  return (
    <div className="flex gap-2">
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Cerca nei documenti..."
        disabled={loading}
        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
      />
      <button
        onClick={onSearch}
        disabled={loading || value.trim().length === 0}
        className="px-5 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? 'Ricerca...' : 'Cerca'}
      </button>
    </div>
  )
}
