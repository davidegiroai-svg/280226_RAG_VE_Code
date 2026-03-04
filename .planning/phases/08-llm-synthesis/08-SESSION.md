# Phase 8: LLM Synthesis — Session Log
**Started:** 2026-03-03 23:18:00
**Ended:** 2026-03-04 09:09:00
**Status:** COMPLETED

## Goal
Implementazione della generazione risposte integrata con LLM (Ollama) usando il parametro `synthesize=true`, con fallback retrieval-only.

## Requirements
- ✅ LLM-01: Integrazione prompt per sintesi dei chunk recuperati
- ✅ LLM-02: Generazione risposta strutturata via LLM
- ✅ LLM-03: Fallback graceful se LLM non disponibile

## Tasks
- [x] Design del prompt di sistema per la RAG
- [x] Implementazione client LLM (Ollama API via `requests`)
- [x] Aggiunta logic di sintesi in `query.py`
- [x] Gestione parametro `synthesize` in QueryRequest
- [ ] Implementazione streaming (opzionale/future)
- [x] Unit tests per LLM Synthesis
- [x] Test di fallback (retrieval-only)
- [x] E2E test con documenti reali

## Files Modified
- ✨ api/app/llm.py (nuovo — `synthesize_answer()` via Ollama /api/chat)
- ✏️ api/app/main.py (parametro `synthesize: bool = False`)
- ✏️ docker-compose.yml (env vars OLLAMA_LLM_MODEL, LLM_TIMEOUT_S)
- ✏️ .env.example (aggiunte variabili LLM)
- ✨ tests/test_llm_synthesis.py (10 test: 5 unitari + 5 integrazione)

## Test Status
- ✅ 34 test totali passed (10 nuovi LLM + 24 precedenti)

## Timeline
- [23:18] Sessione iniziata (Planning)
- [23:25] Analisi dipendenze: `openai` non presente, deciso `requests` per Ollama API
- [23:30] Scrittura piano di implementazione
- [09:00] Implementazione completata, tutti i test green
- [09:09] Sessione chiusa

## Key Decisions
- Uso di `requests` per chiamata diretta a Ollama `/api/chat` (no librerie esterne)
- Prompt di sistema RAG in italiano per contesto Comune di Venezia
- Fallback silenzioso: se Ollama non risponde → `answer = "Retrieval-only response."` + sources
