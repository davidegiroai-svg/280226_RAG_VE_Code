# Phase 12 — Frontend Web RAG Venezia

## Status: COMPLETATA

## Obiettivo
Aggiungere frontend web in italiano per utenti non tecnici: ricerca documenti, upload file, gestione Knowledge Base — accessibile da `http://localhost:3000`.

## Stack Scelto
- Vite 5 + React 18 + TypeScript + Tailwind CSS 3
- Multi-stage Docker: node:20-alpine build → nginx:alpine serve
- Nginx proxy: `/api/*` → `http://api:8000/api/*` con `X-API-Key` iniettata da env var

## File Creati

### Infrastruttura Docker
- `frontend/package.json` — dipendenze npm
- `frontend/tsconfig.json` — TypeScript config
- `frontend/vite.config.ts` — Vite config
- `frontend/tailwind.config.js` — Tailwind content paths
- `frontend/postcss.config.js` — PostCSS con Tailwind + autoprefixer
- `frontend/index.html` — entry HTML
- `frontend/Dockerfile` — multi-stage build
- `frontend/nginx.conf.template` — proxy config con envsubst

### Sorgente React
- `frontend/src/main.tsx` — entry point React
- `frontend/src/App.tsx` — tab navigation responsive
- `frontend/src/index.css` — Tailwind directives + utilities
- `frontend/src/types.ts` — TypeScript interfaces da API
- `frontend/src/api.ts` — client API tipato

### Componenti (`src/components/`)
- `SearchBar.tsx` — input + submit + loading
- `SearchResult.tsx` — card con score badge colorato
- `SearchSettings.tsx` — pannello collassabile: top_k, search_mode, synthesize
- `FileUpload.tsx` — drag & drop + validazione tipo/dimensione
- `KBSelector.tsx` — select popolato da GET /api/v1/kbs
- `DocumentList.tsx` — tabella documenti con status badge
- `Spinner.tsx` — spinner riutilizzabile
- `ErrorMessage.tsx` — messaggio errore riutilizzabile

### Pagine (`src/pages/`)
- `SearchPage.tsx` — ricerca full con KB filter, settings, LLM answer, risultati
- `UploadPage.tsx` — upload con drag & drop e validazione
- `DocumentsPage.tsx` — lista documenti con filtro KB e toggle eliminati
- `KBsPage.tsx` — griglia cards KB con statistiche

### File Modificati
- `docker-compose.yml` — aggiunto servizio `frontend`
- `.env.example` — aggiunto `FRONTEND_PORT`, `FRONTEND_API_KEY`

## FASE 12-A COMPLETATA — Docker + Skeleton React
- package.json, Dockerfile, nginx.conf.template, App.tsx, docker-compose aggiornato

## FASE 12-B COMPLETATA — Pagina Ricerca
- types.ts, api.ts, SearchPage, SearchBar, SearchResult, SearchSettings, KBSelector

## FASE 12-C COMPLETATA — Upload + Documenti + KB
- FileUpload, UploadPage, DocumentList, DocumentsPage, KBsPage

## FASE 12-D COMPLETATA — UX Polish
- Spinner, ErrorMessage riutilizzabili; header responsive sticky; scrollbar-none nav
