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
  graph_enabled?: boolean
  file_type?: string
  year_from?: number
  year_to?: number
  rerank?: boolean
}

export interface RelatedEntity {
  entity_type: string
  display_name: string
  canonical: string
}

export interface RelatedDoc {
  doc_id: string
  source_uri?: string
  titolo?: string
  shared_entities?: string[]
}

export interface Source {
  id: string
  score: number
  kb_namespace: string
  source_path?: string
  excerpt: string
  related_entities?: RelatedEntity[]
  related_docs?: RelatedDoc[]
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
  thinking?: boolean  // true mentre l'LLM elabora (prima del primo token)
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
