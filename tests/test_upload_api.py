"""tests/test_upload_api.py — TDD Phase 7: Upload API

RED:  fallenti prima dell'implementazione in main.py
GREEN: dopo l'aggiunta dei 3 endpoint + upload_log table
"""
import io
import uuid
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _mock_cursor():
    """Mock compatibile con 'with get_db_cursor() as cursor'."""
    mock_cur = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_cur)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx, mock_cur


def _make_file(name: str, content: bytes = b"contenuto di test"):
    """Crea una tupla file per TestClient multipart."""
    return (name, io.BytesIO(content), "application/octet-stream")


# ─────────────────────────────────────────────────────────
# GET /health/ready
# ─────────────────────────────────────────────────────────

class TestHealthReady:

    def test_health_ready_200_quando_db_e_vector_ok(self):
        ctx, mock_cur = _mock_cursor()
        # /health/ready chiama fetchone() due volte: pgvector + count tabelle core
        mock_cur.fetchone.side_effect = [
            {"extname": "vector"},  # Check 1: pgvector presente
            {"count": 3},           # Check 2: 3 tabelle core presenti
        ]

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.get("/health/ready")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"
        assert data["vector"] == "ok"

    def test_health_ready_503_se_vector_mancante(self):
        ctx, mock_cur = _mock_cursor()
        mock_cur.fetchone.return_value = None  # estensione vector non trovata

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.get("/health/ready")

        assert resp.status_code == 503
        assert "vector" in resp.json()["detail"].lower()

    def test_health_ready_503_se_db_non_raggiungibile(self):
        ctx, mock_cur = _mock_cursor()
        mock_cur.execute.side_effect = Exception("connection refused")

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.get("/health/ready")

        assert resp.status_code == 503
        assert "detail" in resp.json()


# ─────────────────────────────────────────────────────────
# GET /api/v1/kbs
# ─────────────────────────────────────────────────────────

class TestListKbs:

    def test_kbs_lista_vuota_se_nessuna_kb(self):
        ctx, mock_cur = _mock_cursor()
        mock_cur.fetchall.return_value = []

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.get("/api/v1/kbs")

        assert resp.status_code == 200
        assert resp.json() == {"kbs": []}

    def test_kbs_ritorna_kb_con_conteggi(self):
        ctx, mock_cur = _mock_cursor()
        mock_cur.fetchall.return_value = [
            {"namespace": "demo", "nome": "Demo KB", "doc_count": 3, "chunk_count": 42}
        ]

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.get("/api/v1/kbs")

        assert resp.status_code == 200
        kbs = resp.json()["kbs"]
        assert len(kbs) == 1
        assert kbs[0]["namespace"] == "demo"
        assert kbs[0]["nome"] == "Demo KB"
        assert kbs[0]["doc_count"] == 3
        assert kbs[0]["chunk_count"] == 42

    def test_kbs_nome_puo_essere_null(self):
        ctx, mock_cur = _mock_cursor()
        mock_cur.fetchall.return_value = [
            {"namespace": "bandi", "nome": None, "doc_count": 0, "chunk_count": 0}
        ]

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.get("/api/v1/kbs")

        assert resp.status_code == 200
        assert resp.json()["kbs"][0]["nome"] is None

    def test_kbs_500_se_db_fallisce(self):
        ctx, mock_cur = _mock_cursor()
        mock_cur.execute.side_effect = Exception("DB error")

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.get("/api/v1/kbs")

        assert resp.status_code == 500


# ─────────────────────────────────────────────────────────
# POST /api/v1/upload
# ─────────────────────────────────────────────────────────

class TestUpload:

    def test_upload_400_se_kb_mancante(self):
        resp = client.post(
            "/api/v1/upload",
            files={"files": _make_file("doc.txt")},
        )
        assert resp.status_code == 400
        assert "kb" in resp.json()["detail"].lower()

    def test_upload_415_tipo_non_supportato(self, tmp_path, monkeypatch):
        monkeypatch.setenv("INBOX_ROOT", str(tmp_path))
        resp = client.post(
            "/api/v1/upload?kb=demo",
            files={"files": _make_file("virus.exe", b"fake exe content")},
        )
        assert resp.status_code == 415
        assert "supportato" in resp.json()["detail"].lower()

    def test_upload_413_file_troppo_grande(self, tmp_path, monkeypatch):
        monkeypatch.setenv("INBOX_ROOT", str(tmp_path))
        monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "1")
        big_content = b"x" * 1_100_000  # 1.1MB > 1MB limite
        resp = client.post(
            "/api/v1/upload?kb=demo",
            files={"files": _make_file("big.pdf", big_content)},
        )
        assert resp.status_code == 413
        assert "grande" in resp.json()["detail"].lower()

    def test_upload_happy_path_ritorna_uuid(self, tmp_path, monkeypatch):
        monkeypatch.setenv("INBOX_ROOT", str(tmp_path))
        ctx, _ = _mock_cursor()

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.post(
                "/api/v1/upload?kb=demo",
                files={"files": _make_file("documento.txt", b"contenuto valido")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "upload_id" in data
        assert "job_id" in data
        assert data["kb"] == "demo"
        assert "documento.txt" in data["files"]
        uuid.UUID(data["upload_id"])  # valida UUID formato
        uuid.UUID(data["job_id"])

    def test_upload_crea_directory_inbox(self, tmp_path, monkeypatch):
        monkeypatch.setenv("INBOX_ROOT", str(tmp_path))
        ctx, _ = _mock_cursor()
        kb_dir = tmp_path / "nuova_kb"
        assert not kb_dir.exists()

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.post(
                "/api/v1/upload?kb=nuova_kb",
                files={"files": _make_file("test.txt", b"testo")},
            )

        assert resp.status_code == 200
        assert kb_dir.exists()

    def test_upload_file_scritto_su_disco(self, tmp_path, monkeypatch):
        monkeypatch.setenv("INBOX_ROOT", str(tmp_path))
        ctx, _ = _mock_cursor()
        contenuto = b"Testo del documento di prova"

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.post(
                "/api/v1/upload?kb=demo",
                files={"files": _make_file("prova.txt", contenuto)},
            )

        assert resp.status_code == 200
        file_sul_disco = tmp_path / "demo" / "prova.txt"
        assert file_sul_disco.exists()
        assert file_sul_disco.read_bytes() == contenuto

    def test_upload_insert_su_upload_log(self, tmp_path, monkeypatch):
        monkeypatch.setenv("INBOX_ROOT", str(tmp_path))
        ctx, mock_cur = _mock_cursor()

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.post(
                "/api/v1/upload?kb=demo",
                files={"files": _make_file("documento.txt", b"contenuto")},
            )

        assert resp.status_code == 200
        sql_calls = [str(c) for c in mock_cur.execute.call_args_list]
        assert any("upload_log" in s for s in sql_calls), (
            f"INSERT INTO upload_log non trovato. Chiamate: {sql_calls}"
        )

    def test_upload_multipli_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("INBOX_ROOT", str(tmp_path))
        ctx, _ = _mock_cursor()

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.post(
                "/api/v1/upload?kb=demo",
                files=[
                    ("files", _make_file("file1.txt", b"primo")),
                    ("files", _make_file("file2.md", b"secondo")),
                    ("files", _make_file("file3.json", b'{"key": "val"}')),
                ],
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["files"]) == 3
        assert set(data["files"]) == {"file1.txt", "file2.md", "file3.json"}

    def test_upload_tutti_i_tipi_supportati(self, tmp_path, monkeypatch):
        monkeypatch.setenv("INBOX_ROOT", str(tmp_path))
        for ext in [".pdf", ".txt", ".md", ".csv", ".json"]:
            ctx, _ = _mock_cursor()
            with patch("app.main.get_db_cursor", return_value=ctx):
                resp = client.post(
                    "/api/v1/upload?kb=demo",
                    files={"files": _make_file(f"doc{ext}", b"contenuto")},
                )
            assert resp.status_code == 200, f"Atteso 200 per {ext}, ricevuto {resp.status_code}"

    def test_upload_genera_meta_json_se_llm_disponibile(self, tmp_path, monkeypatch):
        """POST /upload deve tentare di generare .meta.json via LLM dopo l'upload."""
        monkeypatch.setenv("INBOX_ROOT", str(tmp_path))
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        monkeypatch.setenv("AUTH_ENABLED", "false")

        fake_meta = {"titolo": "Test", "targets": ["Minori"], "ambiti": ["Child guarantee"]}
        ctx, _ = _mock_cursor()

        with patch("app.main.get_db_cursor", return_value=ctx), \
             patch("app.main.extract_metadata_for_file", return_value=fake_meta) as mock_extract, \
             patch("app.main.save_sidecar_meta") as mock_save:
            resp = client.post(
                "/api/v1/upload?kb=test_kb",
                files={"files": ("test.pdf", io.BytesIO(b"%PDF-1.4 test content"), "application/pdf")},
            )

        assert resp.status_code == 200, f"Upload fallito: {resp.text}"
        assert mock_extract.called, "extract_metadata_for_file non \u00e8 stato chiamato"
        assert mock_save.called, "save_sidecar_meta non \u00e8 stato chiamato"


# ─────────────────────────────────────────────────────────
# GET /api/v1/files/{kb_namespace}/{filename}
# ─────────────────────────────────────────────────────────

class TestServeFile:

    def test_serve_file_404_se_file_non_esiste(self, tmp_path, monkeypatch):
        """GET /api/v1/files/kb/file deve restituire 404 se il file non esiste."""
        monkeypatch.setenv("INBOX_ROOT", str(tmp_path))
        resp = client.get("/api/v1/files/demo/inesistente.pdf")
        assert resp.status_code == 404

    def test_serve_file_path_traversal_bloccato(self, monkeypatch):
        """GET /api/v1/files deve bloccare path traversal nel filename."""
        resp = client.get("/api/v1/files/demo/..%2Fsecret.txt")
        assert resp.status_code in (400, 404, 422)

    def test_serve_file_kb_namespace_invalido(self, monkeypatch):
        """GET /api/v1/files deve rifiutare kb_namespace con caratteri non validi."""
        resp = client.get("/api/v1/files/../../etc/bando.pdf")
        assert resp.status_code in (400, 404, 422)

    def test_serve_file_200_se_file_esiste(self, tmp_path, monkeypatch):
        """GET /api/v1/files/kb/file deve restituire 200 + contenuto se il file esiste."""
        monkeypatch.setenv("INBOX_ROOT", str(tmp_path))
        kb_dir = tmp_path / "demo"
        kb_dir.mkdir()
        test_file = kb_dir / "bando.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")
        resp = client.get("/api/v1/files/demo/bando.pdf")
        assert resp.status_code == 200
        assert resp.content == b"%PDF-1.4 test content"

