import type { QueryRequest, QueryResponse, KbInfo, DocumentInfo, UploadResponse } from './types'

// Tutte le chiamate passano per nginx proxy → /api/* viene inoltrato a http://api:8000/api/*
const BASE = ''

export async function searchQuery(req: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${BASE}/api/v1/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Errore query: ${res.status}`)
  }
  return res.json()
}

export async function listKbs(): Promise<KbInfo[]> {
  const res = await fetch(`${BASE}/api/v1/kbs`)
  if (!res.ok) {
    throw new Error(`Errore caricamento knowledge base: ${res.status}`)
  }
  const data = await res.json()
  return data.kbs as KbInfo[]
}

export async function listDocuments(kb?: string): Promise<DocumentInfo[]> {
  const url = kb
    ? `${BASE}/api/v1/documents?kb=${encodeURIComponent(kb)}`
    : `${BASE}/api/v1/documents`
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`Errore caricamento documenti: ${res.status}`)
  }
  const data = await res.json()
  return data.documents as DocumentInfo[]
}

export async function uploadFiles(kb: string, files: File[]): Promise<UploadResponse> {
  const formData = new FormData()
  files.forEach(f => formData.append('files', f))
  const res = await fetch(`${BASE}/api/v1/upload?kb=${encodeURIComponent(kb)}`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Errore upload: ${res.status}` }))
    throw new Error(err.detail || `Errore upload: ${res.status}`)
  }
  return res.json()
}
