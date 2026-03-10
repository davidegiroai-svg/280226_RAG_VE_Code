# Source of Truth & Governance Matrix - RAG VE

> [!NOTE]
> **Tipo Documento:** OPERATIVE SOURCE OF TRUTH / GOVERNANCE INDEX
> **Stato:** Attivo
> **Ambito:** Governance del repository

Questo documento è la bussola per navigare la documentazione del progetto. Definisce cosa è reale, cosa è visione e cosa è storico.

## 1. Hierarchy of Truth (Gerarchia della Verità)

| Livello | Descrizione | File Primari | Affidabile per Claude Code? |
| :--- | :--- | :--- | :--- |
| **0. CODICE** | La verità ultima su ciò che è implementato. | `api/`, `web/`, `docker-compose.yml` | **SÌ** (Primaria) |
| **1. OPERATIVE** | Stato reale corrente e regole attive. | `CLAUDE.md`, `.planning/STATE.md`, `docs/SOURCE_OF_TRUTH.md` | **SÌ** (Secondaria) |
| **2. RUNBOOK** | Istruzioni per far girare il sistema oggi. | `docs_source/docs_generale/DELIVERY_README.md`, `docs/10_run_local.md` | **SÌ** (Operativo) |
| **3. TRANSITION** | Strategia di evoluzione e milestone. | `.planning/ROADMAP.md`, `.planning/PROJECT.md` | **SÌ** (Pianificazione) |
| **4. TARGET** | Visione architetturale e requisiti a regime. | `BRD.md`, `PRD.md`, `SRS.md`, `ARCHITECTURE.md` | **PARZIALE** (Solo visione) |
| **5. HISTORICAL** | Vecchi snapshot e prompt obsoleti. | `docs/03_*`, `docs/90_*`, `docs/*_checklist.md` | **NO** (Ignorare) |

## 2. Document Classification Matrix

| Categoria | Documento | Scopo | Note di affidabilità |
| :--- | :--- | :--- | :--- |
| **Operative** | `CLAUDE.md` | Entry point sessioni e regole. | Riflette M4 (Stabilizzazione). |
| **Operative** | `.planning/STATE.md` | Snapshot reale delle milestone. | M1-M3 DONE, M4 IN PROGRESS. |
| **Runbook** | `DELIVERY_README.md` | Guida al deploy IT. | Contiene solo endpoint e feature reali. |
| **Target State** | `BRD.md` | Visione di Business Target. | Include gap analysis stato attuale. |
| **Target State** | `PRD.md` | Visione di Prodotto Target. | Tutte le feature sono marcate per stato. |
| **Target State** | `SRS.md` | Requisiti Tecnici Target. | Distingue tra requisiti correnti e futuri. |
| **Target State** | `ARCHITECTURE.md`| Architettura Target Finale. | Separa componenti correnti dai futuri. |
| **Historical** | `docs/90_freeze_*` | Freeze post M0. | **NON USARE.** Solo per audit storico. |

---
*Ultimo aggiornamento: 2026-03-10 — Governance RAG VE Reform.*
