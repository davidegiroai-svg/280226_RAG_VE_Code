"""tests/test_auth.py — TDD Phase 11: API Key Authentication

Testa:
- require_api_key(): 401 senza header, 403 key invalida, pass se valida
- Endpoint /api/v1/* protetti: 401/403 senza key
- Endpoint /health e /health/ready: pubblici (nessuna key richiesta)
- AUTH_ENABLED=false: auth saltata per tutti gli endpoint
- hash_api_key(): deterministico
- verify_api_key(): logica DB
- manage_keys: create, revoke, list

RED:  fallenti prima dell'implementazione
GREEN: dopo implementazione in auth.py + main.py
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_api_key, verify_api_key, require_api_key
from app.main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _mock_cursor(row=None):
    """Mock compatibile con 'with get_db_cursor() as cursor'."""
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = row
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_cur)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx, mock_cur


def _auth_bypass():
    """Override per disabilitare l'auth nei test di altri endpoint."""
    return None


# ─────────────────────────────────────────────────────────
# Unit tests: hash_api_key()
# ─────────────────────────────────────────────────────────

class TestHashApiKey:

    def test_hash_deterministico(self):
        """Stessa key → stesso hash ogni volta."""
        h1 = hash_api_key("my-secret-key")
        h2 = hash_api_key("my-secret-key")
        assert h1 == h2

    def test_hash_diverso_per_key_diverse(self):
        h1 = hash_api_key("key-uno")
        h2 = hash_api_key("key-due")
        assert h1 != h2

    def test_hash_e_stringa_esadecimale_64_char(self):
        h = hash_api_key("qualsiasi-key")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_non_contiene_key_raw(self):
        raw = "supersecretkey"
        h = hash_api_key(raw)
        assert raw not in h


# ─────────────────────────────────────────────────────────
# Unit tests: verify_api_key()
# ─────────────────────────────────────────────────────────

class TestVerifyApiKey:

    def test_verify_ritorna_true_se_key_attiva(self):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {"id": "uuid-123"}

        result = verify_api_key("abcdef1234", mock_cur)

        assert result is True

    def test_verify_ritorna_false_se_key_non_trovata(self):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None

        result = verify_api_key("key-inesistente", mock_cur)

        assert result is False

    def test_verify_esegue_query_con_hash(self):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None

        verify_api_key("myhash", mock_cur)

        call_args = mock_cur.execute.call_args
        sql, params = call_args[0]
        assert "myhash" in params
        assert "is_active" in sql.lower()

    def test_verify_controlla_scadenza(self):
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None

        verify_api_key("myhash", mock_cur)

        call_args = mock_cur.execute.call_args
        sql = call_args[0][0]
        assert "expires_at" in sql.lower()


# ─────────────────────────────────────────────────────────
# Integration tests: require_api_key con endpoint reali
# ─────────────────────────────────────────────────────────

class TestRequireApiKey:

    def test_401_senza_header_x_api_key(self, monkeypatch):
        """Nessun header → 401 Unauthorized."""
        monkeypatch.setenv("AUTH_ENABLED", "true")
        resp = client.post("/api/v1/query", json={"query": "bando"})
        assert resp.status_code == 401
        assert "X-API-Key" in resp.json()["detail"] or "Autenticazione" in resp.json()["detail"]

    def test_403_con_key_invalida(self, monkeypatch):
        """Header presente ma key non nel DB → 403 Forbidden."""
        monkeypatch.setenv("AUTH_ENABLED", "true")
        ctx, mock_cur = _mock_cursor(row=None)  # key non trovata

        with patch("app.auth.get_db_cursor", return_value=ctx):
            resp = client.post(
                "/api/v1/query",
                json={"query": "bando"},
                headers={"X-API-Key": "key-invalida"},
            )

        assert resp.status_code == 403

    def test_200_con_key_valida(self, monkeypatch):
        """Header con key valida → endpoint risponde normalmente."""
        monkeypatch.setenv("AUTH_ENABLED", "true")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")

        # Mock auth: key trovata nel DB
        auth_ctx, auth_cur = _mock_cursor(row={"id": "key-uuid"})
        # Mock query DB: nessun risultato
        query_ctx, query_cur = _mock_cursor(row=None)
        query_cur.fetchall.return_value = []

        with patch("app.auth.get_db_cursor", return_value=auth_ctx):
            with patch("app.main.get_db_cursor", return_value=query_ctx):
                with patch("app.main.embed_text", return_value=([0.0]*768, "dummy", 768)):
                    resp = client.post(
                        "/api/v1/query",
                        json={"query": "bando"},
                        headers={"X-API-Key": "valid-key-123"},
                    )

        assert resp.status_code == 200

    def test_auth_disabled_accesso_senza_key(self, monkeypatch):
        """AUTH_ENABLED=false → endpoint accessibile senza X-API-Key."""
        monkeypatch.setenv("AUTH_ENABLED", "false")
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")

        query_ctx, query_cur = _mock_cursor(row=None)
        query_cur.fetchall.return_value = []

        with patch("app.main.get_db_cursor", return_value=query_ctx):
            with patch("app.main.embed_text", return_value=([0.0]*768, "dummy", 768)):
                resp = client.post("/api/v1/query", json={"query": "bando"})

        assert resp.status_code == 200

    def test_health_pubblico_senza_key(self, monkeypatch):
        """GET /health non richiede X-API-Key."""
        monkeypatch.setenv("AUTH_ENABLED", "true")

        with patch("app.main.test_connection", return_value=True):
            resp = client.get("/health")

        assert resp.status_code == 200

    def test_health_ready_pubblico_senza_key(self, monkeypatch):
        """GET /health/ready non richiede X-API-Key."""
        monkeypatch.setenv("AUTH_ENABLED", "true")
        ctx, mock_cur = _mock_cursor(row={"extname": "vector"})

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.get("/health/ready")

        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────
# Endpoint /api/v1/kbs, /documents, /upload protetti
# ─────────────────────────────────────────────────────────

class TestEndpointProtetti:

    def test_kbs_401_senza_key(self, monkeypatch):
        monkeypatch.setenv("AUTH_ENABLED", "true")
        resp = client.get("/api/v1/kbs")
        assert resp.status_code == 401

    def test_documents_401_senza_key(self, monkeypatch):
        monkeypatch.setenv("AUTH_ENABLED", "true")
        resp = client.get("/api/v1/documents")
        assert resp.status_code == 401

    def test_upload_401_senza_key(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AUTH_ENABLED", "true")
        monkeypatch.setenv("INBOX_ROOT", str(tmp_path))
        import io
        resp = client.post(
            "/api/v1/upload?kb=demo",
            files={"files": ("test.txt", io.BytesIO(b"contenuto"), "text/plain")},
        )
        assert resp.status_code == 401

    def test_kbs_200_con_key_valida(self, monkeypatch):
        """GET /api/v1/kbs con key valida → 200."""
        monkeypatch.setenv("AUTH_ENABLED", "true")

        # Mock auth: key trovata
        auth_ctx, _ = _mock_cursor(row={"id": "key-uuid"})
        # Mock query kbs: lista vuota
        kbs_ctx, kbs_cur = _mock_cursor()
        kbs_cur.fetchall.return_value = []

        with patch("app.auth.get_db_cursor", return_value=auth_ctx):
            with patch("app.main.get_db_cursor", return_value=kbs_ctx):
                resp = client.get(
                    "/api/v1/kbs",
                    headers={"X-API-Key": "valid-key"},
                )

        assert resp.status_code == 200

    def test_key_revocata_403(self, monkeypatch):
        """Key revocata (is_active=FALSE) → 403."""
        monkeypatch.setenv("AUTH_ENABLED", "true")
        # DB non trova la key (is_active=FALSE filtrata dalla query)
        auth_ctx, _ = _mock_cursor(row=None)

        with patch("app.auth.get_db_cursor", return_value=auth_ctx):
            resp = client.get(
                "/api/v1/kbs",
                headers={"X-API-Key": "revoked-key"},
            )

        assert resp.status_code == 403

    def test_key_scaduta_403(self, monkeypatch):
        """Key scaduta (expires_at in passato) → 403."""
        monkeypatch.setenv("AUTH_ENABLED", "true")
        # DB non trova la key (expires_at < NOW() filtrata dalla query)
        auth_ctx, _ = _mock_cursor(row=None)

        with patch("app.auth.get_db_cursor", return_value=auth_ctx):
            resp = client.get(
                "/api/v1/documents",
                headers={"X-API-Key": "expired-key"},
            )

        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────
# Unit tests: manage_keys (create, revoke, list)
# ─────────────────────────────────────────────────────────

class TestManageKeys:

    def test_create_inserisce_hash_nel_db(self, monkeypatch):
        """cmd_create() deve inserire il key_hash nel DB, non la key raw."""
        from app.manage_keys import cmd_create

        mock_row = {"id": "uuid-abc", "name": "test-key", "created_at": "2026-01-01"}
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = mock_row
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("app.manage_keys._get_conn", return_value=mock_conn):
            with patch("builtins.print"):  # silenzia output
                cmd_create("test-key")

        # Verifica che execute sia stato chiamato con un hash (64 char hex), non una UUID raw
        call_args = mock_cur.execute.call_args
        params = call_args[0][1]
        key_hash_salvato = params[0]
        assert len(key_hash_salvato) == 64
        assert all(c in "0123456789abcdef" for c in key_hash_salvato)

    def test_create_non_salva_key_raw(self, monkeypatch):
        """La key raw NON deve mai apparire nei parametri SQL."""
        from app.manage_keys import cmd_create
        import uuid as uuid_mod

        # Intercetta la key raw generata
        chiave_raw = []
        orig_uuid4 = uuid_mod.uuid4

        def mock_uuid4():
            u = orig_uuid4()
            chiave_raw.append(str(u))
            return u

        mock_row = {"id": "uuid-abc", "name": "test-key", "created_at": "2026-01-01"}
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = mock_row
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("app.manage_keys._get_conn", return_value=mock_conn):
            with patch("app.manage_keys.uuid.uuid4", side_effect=mock_uuid4):
                with patch("builtins.print"):
                    cmd_create("test-key")

        # Verifica: key raw non è nei parametri SQL
        if chiave_raw:
            call_args = mock_cur.execute.call_args
            params = call_args[0][1]
            assert chiave_raw[0] not in params, "La key raw non deve essere salvata nel DB!"

    def test_revoke_aggiorna_is_active(self, monkeypatch):
        """cmd_revoke() deve aggiornare is_active=FALSE nel DB."""
        from app.manage_keys import cmd_revoke

        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {"id": "key-uuid", "name": "my-key"}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("app.manage_keys._get_conn", return_value=mock_conn):
            with patch("builtins.print"):
                cmd_revoke("key-uuid-123")

        call_args = mock_cur.execute.call_args
        sql = call_args[0][0]
        assert "is_active" in sql.lower()
        assert "false" in sql.lower()

    def test_list_non_mostra_key_hash(self, monkeypatch):
        """cmd_list() non deve mai stampare il key_hash."""
        from app.manage_keys import cmd_list

        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            {
                "id": "uuid-1",
                "name": "frontend",
                "created_at": "2026-01-01 10:00:00+00",
                "expires_at": None,
                "revoked_at": None,
                "is_active": True,
            }
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        output_lines = []
        with patch("app.manage_keys._get_conn", return_value=mock_conn):
            with patch("builtins.print", side_effect=lambda *args: output_lines.append(str(args))):
                cmd_list()

        output_str = " ".join(output_lines)
        # "key_hash" non deve apparire nell'output
        assert "key_hash" not in output_str.lower()
        # Il nome deve apparire
        assert "frontend" in output_str
