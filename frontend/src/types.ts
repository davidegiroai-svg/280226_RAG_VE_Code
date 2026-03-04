export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface QueryRequest {
  query: string
  kb?: string
  top_k?: number
  synthesize?: boolean
  search_mode?: 'vector' | 'fts' | 'hybrid'
  history?: ChatMessage[]
}

export interface Source {
  id: string
  score: number
  kb_namespace: string
  source_path?: string
  excerpt: string
}

export interface QueryResponse {
  answer: string
  sources: Source[]
}

// Messaggio nella chat UI (estende ChatMessage con fonti opzionali per l'assistente)
export interface UIChatMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
}

export interface KbInfo {
  namespace: string
  nome?: string
  doc_count: number
  chunk_count: number
}

export interface DocumentInfo {
  id: string
  kb_namespace: string
  source_path?: string
  titolo?: string
  ingest_status?: string
  is_deleted: boolean
  created_at?: string
}

export interface UploadResponse {
  upload_id: string
  job_id: string
  kb: string
  files: string[]
}
