"""tests/test_watcher.py — TDD Phase 9: Watcher

Testa l'handler filesystem e ingest_single_file con mock.
NON richiede filesystem reale: tutto mockato.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi.testclient import TestClient

from app.watcher import InboxHandler, soft_delete_document
from app.ingest_fs import ingest_single_file, update_ingest_status
from app.main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _make_event(path: str, is_dir: bool = False):
    """Crea un mock di evento watchdog."""
    event = MagicMock()
    event.src_path = path
    event.is_directory = is_dir
    return event


def _mock_ingest_conn(kb_exists: bool = True, doc_is_new: bool = True):
    """Mock per get_conn() usato in ingest_single_file.

    Returns (mock_conn, mock_cur).
    """
    mock_cur = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_cur)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    # ensure_kb: SELECT → found o INSERT + RETURNING
    if kb_exists:
        mock_cur.fetchone.side_effect = [
            ("kb-id-123",),   # ensure_kb SELECT trovato
            ("doc-id-456",),  # upsert_document INSERT RETURNING (nuovo doc)
        ]
    else:
        mock_cur.fetchone.side_effect = [
            None,             # ensure_kb SELECT → non trovato
            ("kb-id-new",),   # ensure_kb INSERT RETURNING
            ("doc-id-456",),  # upsert_document INSERT RETURNING
        ]

    if not doc_is_new:
        # Documenti già esistente: INSERT DO NOTHING → fetchone=None, poi SELECT
        if kb_exists:
            mock_cur.fetchone.side_effect = [
                ("kb-id-123",),   # ensure_kb
                None,             # upsert INSERT DO NOTHING → no RETURNING
                ("doc-id-456",),  # upsert SELECT existing
            ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_ctx

    return mock_conn, mock_cur


def _mock_db_cursor(rows=None):
    """Mock compatibile con 'with get_db_cursor() as cursor'."""
    mock_cur = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_cur)
    ctx.__exit__ = MagicMock(return_value=False)
    if rows is not None:
        mock_cur.fetchall.return_value = rows
    return ctx, mock_cur


# ─────────────────────────────────────────────────────────
# Test InboxHandler — eventi filesystem
# ─────────────────────────────────────────────────────────

class TestInboxHandler:

    def test_file_created_chiama_ingest(self):
        """on_created() su file .txt chiama ingest_single_file con path e KB corretti."""
        handler = InboxHandler("/data/inbox")
        event = _make_event("/data/inbox/demo/documento.txt")

        with patch("app.watcher.ingest_single_file") as mock_ingest:
            mock_ingest.return_value = {"status": "done", "chunks_inserted": 3}
            handler.on_created(event)

        mock_ingest.assert_called_once_with(
            Path("/data/inbox/demo/documento.txt"), "demo"
        )

    def test_file_created_ignora_directory(self):
        """on_created() su directory non chiama ingest."""
        handler = InboxHandler("/data/inbox")
        event = _make_event("/data/inbox/demo/", is_dir=True)

        with patch("app.watcher.ingest_single_file") as mock_ingest:
            handler.on_created(event)

        mock_ingest.assert_not_called()

    def test_file_deleted_chiama_soft_delete(self):
        """on_deleted() su file supportato chiama soft_delete_document con source_path."""
        handler = InboxHandler("/data/inbox")
        event = _make_event("/data/inbox/demo/vecchio.pdf")

        with patch("app.watcher.soft_delete_document") as mock_delete:
            handler.on_deleted(event)

        mock_delete.assert_called_once_with("/data/inbox/demo/vecchio.pdf")

    def test_file_deleted_ignora_directory(self):
        """on_deleted() su directory non chiama soft_delete_document."""
        handler = InboxHandler("/data/inbox")
        event = _make_event("/data/inbox/demo/", is_dir=True)

        with patch("app.watcher.soft_delete_document") as mock_delete:
            handler.on_deleted(event)

        mock_delete.assert_not_called()

    def test_filtro_estensioni_ignora_exe(self):
        """File .exe non supportato: ingest NON viene chiamato."""
        handler = InboxHandler("/data/inbox")
        event = _make_event("/data/inbox/demo/virus.exe")

        with patch("app.watcher.ingest_single_file") as mock_ingest:
            handler.on_created(event)

        mock_ingest.assert_not_called()

    def test_filtro_estensioni_ignora_docx(self):
        """File .docx non supportato: ingest NON viene chiamato."""
        handler = InboxHandler("/data/inbox")
        event = _make_event("/data/inbox/demo/relazione.docx")

        with patch("app.watcher.ingest_single_file") as mock_ingest:
            handler.on_created(event)

        mock_ingest.assert_not_called()

    def test_filtro_estensioni_processa_pdf(self):
        """File .pdf supportato: ingest VIENE chiamato."""
        handler = InboxHandler("/data/inbox")
        event = _make_event("/data/inbox/bandi/delibera.pdf")

        with patch("app.watcher.ingest_single_file") as mock_ingest:
            mock_ingest.return_value = {"status": "done", "chunks_inserted": 5}
            handler.on_created(event)

        mock_ingest.assert_called_once_with(Path("/data/inbox/bandi/delibera.pdf"), "bandi")

    def test_filtro_estensioni_processa_tutti_i_tipi(self):
        """Tutti i tipi supportati vengono processati."""
        handler = InboxHandler("/data/inbox")
        for ext in [".txt", ".md", ".csv", ".json", ".pdf"]:
            event = _make_event(f"/data/inbox/demo/doc{ext}")
            with patch("app.watcher.ingest_single_file") as mock_ingest:
                mock_ingest.return_value = {"status": "done", "chunks_inserted": 1}
                handler.on_created(event)
            mock_ingest.assert_called_once(), f"Atteso ingest per {ext}"

    def test_ingest_error_non_propaga_eccezione(self):
        """Errore nell'ingest non deve far crashare il watcher."""
        handler = InboxHandler("/data/inbox")
        event = _make_event("/data/inbox/demo/corrotto.txt")

        with patch("app.watcher.ingest_single_file", side_effect=RuntimeError("errore embedding")):
            # Non deve sollevare eccezione — il watcher deve continuare
            handler.on_created(event)  # se arriva qui senza eccezione: OK


# ─────────────────────────────────────────────────────────
# Test ingest_single_file — transizioni ingest_status
# ─────────────────────────────────────────────────────────

class TestIngestSingleFile:

    def test_ingest_status_processing_poi_done(self):
        """ingest_single_file aggiorna lo status: processing → done."""
        mock_conn, mock_cur = _mock_ingest_conn()
        file_path = Path("/data/inbox/demo/prova.txt")

        with patch("app.ingest_fs.get_conn", return_value=mock_conn):
            with patch("app.ingest_fs.read_text_file", return_value="Testo di test valido"):
                with patch("app.ingest_fs.insert_chunks", return_value=3):
                    with patch("app.ingest_fs.update_ingest_status") as mock_status:
                        result = ingest_single_file(file_path, "demo")

        assert result["status"] == "done"
        assert result["chunks_inserted"] == 3

        # Verifica sequenza: processing → done
        status_calls = [c.args[2] for c in mock_status.call_args_list]
        assert "processing" in status_calls, f"'processing' atteso tra: {status_calls}"
        assert "done" in status_calls, f"'done' atteso tra: {status_calls}"
        # L'ordine deve essere: processing prima di done
        idx_processing = status_calls.index("processing")
        idx_done = status_calls.index("done")
        assert idx_processing < idx_done

    def test_ingest_status_error_su_fallimento_insert_chunks(self):
        """Se insert_chunks solleva eccezione, ingest_single_file propaga l'errore."""
        mock_conn, mock_cur = _mock_ingest_conn()
        file_path = Path("/data/inbox/demo/rotto.txt")

        with patch("app.ingest_fs.get_conn", return_value=mock_conn):
            with patch("app.ingest_fs.read_text_file", return_value="Testo valido"):
                with patch("app.ingest_fs.insert_chunks", side_effect=RuntimeError("embedding error")):
                    with pytest.raises(RuntimeError, match="embedding error"):
                        ingest_single_file(file_path, "demo")

        # Il rollback deve essere chiamato
        mock_conn.rollback.assert_called()

    def test_ingest_file_vuoto_ritorna_skipped(self):
        """File di testo vuoto viene saltato senza errore."""
        mock_conn, mock_cur = _mock_ingest_conn()
        file_path = Path("/data/inbox/demo/vuoto.txt")

        with patch("app.ingest_fs.get_conn", return_value=mock_conn):
            with patch("app.ingest_fs.read_text_file", return_value="   \n  "):
                result = ingest_single_file(file_path, "demo")

        assert result["status"] == "skipped"
        assert result["reason"] == "file vuoto"

    def test_ingest_estensione_non_supportata_ritorna_skipped(self):
        """File con estensione non supportata viene saltato immediatamente."""
        file_path = Path("/data/inbox/demo/documento.exe")
        result = ingest_single_file(file_path, "demo")
        assert result["status"] == "skipped"
        assert result["reason"] == "estensione non supportata"

    def test_ingest_documento_esistente_ritorna_existing(self):
        """File già indicizzato (upsert DO NOTHING) ritorna status=existing."""
        mock_conn, mock_cur = _mock_ingest_conn(doc_is_new=False)
        file_path = Path("/data/inbox/demo/esistente.txt")

        with patch("app.ingest_fs.get_conn", return_value=mock_conn):
            with patch("app.ingest_fs.read_text_file", return_value="Testo già indicizzato"):
                result = ingest_single_file(file_path, "demo")

        assert result["status"] == "existing"
        assert result["is_new"] is False


# ─────────────────────────────────────────────────────────
# Test soft_delete_document
# ─────────────────────────────────────────────────────────

class TestSoftDeleteDocument:

    def test_soft_delete_aggiorna_is_deleted(self):
        """soft_delete_document esegue UPDATE is_deleted=TRUE e DELETE chunks."""
        mock_cur = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_cur)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_cur.fetchone.return_value = ("doc-id-789",)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_ctx

        with patch("app.watcher.get_conn", return_value=mock_conn):
            soft_delete_document("/data/inbox/demo/vecchio.txt")

        execute_calls = [str(c) for c in mock_cur.execute.call_args_list]
        assert any("is_deleted" in s for s in execute_calls), (
            f"UPDATE is_deleted non trovato: {execute_calls}"
        )
        assert any("DELETE FROM chunks" in s for s in execute_calls), (
            f"DELETE chunks non trovato: {execute_calls}"
        )
        mock_conn.commit.assert_called_once()

    def test_soft_delete_documento_non_trovato_non_solleva(self):
        """Se il documento non esiste, soft_delete_document non solleva eccezione."""
        mock_cur = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_cur)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_cur.fetchone.return_value = None  # documento non trovato

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_ctx

        with patch("app.watcher.get_conn", return_value=mock_conn):
            # Non deve sollevare eccezione
            soft_delete_document("/data/inbox/demo/non_esiste.txt")


# ─────────────────────────────────────────────────────────
# Test GET /api/v1/documents
# ─────────────────────────────────────────────────────────

class TestDocumentsEndpoint:

    def test_documents_lista_vuota(self):
        """GET /api/v1/documents ritorna lista vuota se nessun documento."""
        ctx, mock_cur = _mock_db_cursor(rows=[])
        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.get("/api/v1/documents")
        assert resp.status_code == 200
        assert resp.json() == {"documents": []}

    def test_documents_ritorna_documenti(self):
        """GET /api/v1/documents ritorna documenti con campi corretti."""
        ctx, mock_cur = _mock_db_cursor(rows=[{
            "id": "uuid-doc-1",
            "kb_namespace": "demo",
            "source_path": "/data/inbox/demo/bandi.pdf",
            "titolo": "bandi.pdf",
            "ingest_status": "done",
            "is_deleted": False,
            "created_at": "2026-03-04T09:00:00+00:00",
        }])
        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.get("/api/v1/documents")

        assert resp.status_code == 200
        docs = resp.json()["documents"]
        assert len(docs) == 1
        assert docs[0]["kb_namespace"] == "demo"
        assert docs[0]["ingest_status"] == "done"
        assert docs[0]["is_deleted"] is False

    def test_documents_filtro_kb(self):
        """GET /api/v1/documents?kb=demo passa il filtro al SQL."""
        ctx, mock_cur = _mock_db_cursor(rows=[])
        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.get("/api/v1/documents?kb=demo")
        assert resp.status_code == 200
        # Verifica che il namespace sia passato come parametro SQL
        sql_calls = [str(c) for c in mock_cur.execute.call_args_list]
        assert any("demo" in str(c.args) for c in mock_cur.execute.call_args_list)

    def test_documents_filtro_deleted(self):
        """GET /api/v1/documents?deleted=true ritorna solo documenti soft-deleted."""
        ctx, mock_cur = _mock_db_cursor(rows=[{
            "id": "uuid-del-1",
            "kb_namespace": "demo",
            "source_path": "/data/inbox/demo/vecchio.txt",
            "titolo": "vecchio.txt",
            "ingest_status": "indexed",
            "is_deleted": True,
            "created_at": "2026-03-01T08:00:00+00:00",
        }])
        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.get("/api/v1/documents?deleted=true")

        assert resp.status_code == 200
        docs = resp.json()["documents"]
        assert len(docs) == 1
        assert docs[0]["is_deleted"] is True

    def test_documents_500_se_db_fallisce(self):
        """GET /api/v1/documents ritorna 500 se DB non risponde."""
        ctx, mock_cur = _mock_db_cursor()
        mock_cur.execute.side_effect = Exception("DB error")
        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.get("/api/v1/documents")
        assert resp.status_code == 500
