import { useState } from 'react'
import SearchPage from './pages/SearchPage'
import UploadPage from './pages/UploadPage'
import DocumentsPage from './pages/DocumentsPage'
import KBsPage from './pages/KBsPage'

type Tab = 'search' | 'upload' | 'documents' | 'kbs'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'search', label: 'Ricerca', icon: '🔍' },
  { id: 'upload', label: 'Upload', icon: '📤' },
  { id: 'documents', label: 'Documenti', icon: '📄' },
  { id: 'kbs', label: 'Knowledge Base', icon: '🗂️' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('search')

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4">
          {/* Logo row */}
          <div className="flex items-center justify-between py-3 pb-0">
            <div className="flex items-center gap-2">
              <span className="text-2xl" aria-hidden>🏛️</span>
              <div>
                <h1 className="text-base sm:text-lg font-bold text-blue-900 leading-tight">RAG Venezia</h1>
                <p className="text-xs text-gray-400 leading-tight hidden sm:block">
                  Ricerca documenti — Comune di Venezia
                </p>
              </div>
            </div>
          </div>

          {/* Tab navigation — scrollable on mobile */}
          <nav className="flex gap-0 overflow-x-auto scrollbar-none -mx-1 px-1" aria-label="Navigazione principale">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                aria-current={activeTab === tab.id ? 'page' : undefined}
                className={`flex items-center gap-1.5 px-3 sm:px-4 py-2.5 text-xs sm:text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-4 py-6">
        {activeTab === 'search' && <SearchPage />}
        {activeTab === 'upload' && <UploadPage />}
        {activeTab === 'documents' && <DocumentsPage />}
        {activeTab === 'kbs' && <KBsPage />}
      </main>
    </div>
  )
}
