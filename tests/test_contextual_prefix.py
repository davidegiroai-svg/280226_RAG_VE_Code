"""Test build_context_prefix() e integrazione embedding contestuale."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Fix sys.path per pytest in Docker
parent_dir = str(Path(__file__).resolve().parent.parent / "api")
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.ingest_fs import build_context_prefix, MAX_PREFIX_LEN


def test_build_context_prefix_full():
    """Tutti i campi popolati → prefisso completo."""
    result = build_context_prefix("demo", "Bando_CG_2025.pdf", "pdf")
    assert result == "[demo | Bando_CG_2025.pdf | pdf] "


def test_build_context_prefix_no_titolo():
    """Titolo vuoto → omesso dal prefisso."""
    result = build_context_prefix("bandi", "", "txt")
    assert result == "[bandi | txt] "


def test_build_context_prefix_all_empty():
    """Tutti vuoti → prefisso minimo."""
    result = build_context_prefix("", "", "")
    assert result == "[] "


def test_build_context_prefix_truncation():
    """Titolo molto lungo → troncato a MAX_PREFIX_LEN."""
    long_title = "A" * 200
    result = build_context_prefix("demo", long_title, "pdf")
    assert len(result) <= MAX_PREFIX_LEN


def test_build_context_prefix_with_tipo_documento():
    """Con tipo_documento → incluso nel prefisso."""
    result = build_context_prefix("bandi", "Avviso.pdf", "pdf", tipo_documento="avviso_bando")
    assert "avviso_bando" in result
    assert result.startswith("[")
    assert result.endswith("] ")


def test_build_context_prefix_with_targets():
    """Con targets → primi 3 inclusi nel prefisso."""
    result = build_context_prefix(
        "bandi", "Doc.pdf", "pdf",
        targets=["Famiglie", "Minori", "Anziani", "Donne"],
    )
    assert "Famiglie" in result
    assert "Minori" in result
    assert "Anziani" in result
    # Quarto target non incluso (max 3)
    assert "Donne" not in result


def test_build_context_prefix_with_metadata_full():
    """Tutti i campi + metadata → formato completo."""
    result = build_context_prefix(
        "bandi", "Avviso_FSE.pdf", "pdf",
        tipo_documento="avviso_bando",
        targets=["Famiglie", "Minori"],
    )
    assert result == "[bandi | Avviso_FSE.pdf | pdf | avviso_bando | Famiglie Minori] "


# --- Test integrazione insert_chunks con prefix ---

def test_insert_chunks_text_embeds_with_prefix(monkeypatch):
    """embed_texts riceve testo CON prefisso contestuale."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    from app.ingest_fs import insert_chunks

    captured_texts = []
    original_embed = None

    def fake_embed_texts(texts):
        captured_texts.extend(texts)
        from app.embedding import embed_texts as real_embed
        return real_embed(texts)

    mock_cur = MagicMock()
    with patch("app.ingest_fs.embed_texts", side_effect=fake_embed_texts):
        with patch("app.ingest_fs.read_sidecar_meta", return_value={}):
            insert_chunks(
                mock_cur, "kb-uuid", "demo", "doc-uuid",
                "/data/inbox/demo/test.txt", "test.txt",
                "Testo di esempio per il bando comunale.",
                titolo="test.txt",
            )

    assert len(captured_texts) > 0
    # Ogni testo inviato a embed_texts deve iniziare col prefisso
    for t in captured_texts:
        assert t.startswith("[demo | test.txt | txt] ")


def test_insert_chunks_text_stores_raw_testo(monkeypatch):
    """INSERT nel DB contiene testo originale SENZA prefisso."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    from app.ingest_fs import insert_chunks

    mock_cur = MagicMock()
    raw_text = "Testo di esempio per il bando comunale."

    with patch("app.ingest_fs.read_sidecar_meta", return_value={}):
        insert_chunks(
            mock_cur, "kb-uuid", "demo", "doc-uuid",
            "/data/inbox/demo/test.txt", "test.txt",
            raw_text, titolo="test.txt",
        )

    # Verifica che la INSERT contenga il testo raw (quarto parametro posizionale dopo doc_id, kb_id, kb_namespace, chunk_index)
    assert mock_cur.execute.called
    insert_call = mock_cur.execute.call_args_list[-1]
    params = insert_call[0][1]  # tuple dei parametri SQL
    # params[4] = testo (5° parametro: doc_id, kb_id, kb_namespace, chunk_index, testo)
    assert params[4] == raw_text
    # Non deve contenere il prefisso
    assert not params[4].startswith("[")


def test_insert_chunks_backward_compatible(monkeypatch):
    """Chiamata senza titolo kwarg → funziona con prefisso minimo."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    from app.ingest_fs import insert_chunks

    mock_cur = MagicMock()
    with patch("app.ingest_fs.read_sidecar_meta", return_value={}):
        count = insert_chunks(
            mock_cur, "kb-uuid", "demo", "doc-uuid",
            "/data/inbox/demo/test.txt", "test.txt",
            "Testo di esempio.",
        )

    assert count > 0
    assert mock_cur.execute.called


# --- Test auto-classificazione nel pipeline ingest ---

def _make_mock_conn():
    """Crea mock connection + cursor con ensure_kb e upsert_document funzionanti."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    # ensure_kb → kb_id fittizio
    mock_cur.fetchone.side_effect = [
        ("kb-uuid-123",),   # ensure_kb SELECT
        ("doc-uuid-456", ), # upsert_document RETURNING
    ]
    return mock_conn, mock_cur


def test_auto_classify_called_when_no_sidecar(monkeypatch, tmp_path):
    """Con AUTO_CLASSIFY_ENABLED=true e no sidecar, extract_metadata_for_file viene chiamata."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    monkeypatch.setenv("AUTO_CLASSIFY_ENABLED", "true")

    # Crea file di test
    test_file = tmp_path / "bando_test.txt"
    test_file.write_text("Contenuto del bando di prova per test.", encoding="utf-8")

    mock_extract = MagicMock(return_value={"tipo_documento": "avviso_bando", "targets": ["Famiglie"]})
    mock_save = MagicMock()

    with patch("app.ingest_fs.get_conn") as mock_get_conn, \
         patch("app.ingest_fs.read_sidecar_meta", return_value={}), \
         patch("app.ingest_fs.insert_chunks", return_value=3), \
         patch("app.ingest_fs._graph_extract_and_save"), \
         patch("app.metadata_extractor.extract_metadata_for_file", mock_extract), \
         patch("app.metadata_extractor.save_sidecar_meta", mock_save):
        mock_conn, mock_cur = _make_mock_conn()
        mock_get_conn.return_value = mock_conn

        from app.ingest_fs import ingest_single_file
        result = ingest_single_file(test_file, "demo")

    mock_extract.assert_called_once()
    mock_save.assert_called_once()
    assert result["status"] == "done"


def test_auto_classify_skipped_when_sidecar_exists(monkeypatch, tmp_path):
    """Se il sidecar esiste già, extract_metadata_for_file NON viene chiamata."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    monkeypatch.setenv("AUTO_CLASSIFY_ENABLED", "true")

    test_file = tmp_path / "bando_test.txt"
    test_file.write_text("Contenuto del bando.", encoding="utf-8")

    existing_sidecar = {"tipo_documento": "avviso_bando", "targets": ["Minori"]}
    mock_extract = MagicMock()

    with patch("app.ingest_fs.get_conn") as mock_get_conn, \
         patch("app.ingest_fs.read_sidecar_meta", return_value=existing_sidecar), \
         patch("app.ingest_fs.insert_chunks", return_value=3), \
         patch("app.ingest_fs._graph_extract_and_save"), \
         patch("app.metadata_extractor.extract_metadata_for_file", mock_extract):
        mock_conn, mock_cur = _make_mock_conn()
        mock_get_conn.return_value = mock_conn

        from app.ingest_fs import ingest_single_file
        result = ingest_single_file(test_file, "demo")

    mock_extract.assert_not_called()


def test_auto_classify_skipped_when_disabled(monkeypatch, tmp_path):
    """Con AUTO_CLASSIFY_ENABLED=false (default), extract NON viene chiamata."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    # AUTO_CLASSIFY_ENABLED non settato → default "false"
    monkeypatch.delenv("AUTO_CLASSIFY_ENABLED", raising=False)

    test_file = tmp_path / "bando_test.txt"
    test_file.write_text("Contenuto del bando.", encoding="utf-8")

    mock_extract = MagicMock()

    with patch("app.ingest_fs.get_conn") as mock_get_conn, \
         patch("app.ingest_fs.read_sidecar_meta", return_value={}), \
         patch("app.ingest_fs.insert_chunks", return_value=3), \
         patch("app.ingest_fs._graph_extract_and_save"), \
         patch("app.metadata_extractor.extract_metadata_for_file", mock_extract):
        mock_conn, mock_cur = _make_mock_conn()
        mock_get_conn.return_value = mock_conn

        from app.ingest_fs import ingest_single_file
        result = ingest_single_file(test_file, "demo")

    mock_extract.assert_not_called()


def test_auto_classify_fallback_saves_nothing(monkeypatch, tmp_path):
    """Se extract ritorna fallback (tipo_documento=None), save_sidecar_meta NON viene chiamata."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    monkeypatch.setenv("AUTO_CLASSIFY_ENABLED", "true")

    test_file = tmp_path / "bando_test.txt"
    test_file.write_text("Contenuto del bando.", encoding="utf-8")

    # Fallback: tipo_documento è None
    fallback_result = {"tipo_documento": None, "targets": [], "ambiti": []}
    mock_extract = MagicMock(return_value=fallback_result)
    mock_save = MagicMock()

    with patch("app.ingest_fs.get_conn") as mock_get_conn, \
         patch("app.ingest_fs.read_sidecar_meta", return_value={}), \
         patch("app.ingest_fs.insert_chunks", return_value=3), \
         patch("app.ingest_fs._graph_extract_and_save"), \
         patch("app.metadata_extractor.extract_metadata_for_file", mock_extract), \
         patch("app.metadata_extractor.save_sidecar_meta", mock_save):
        mock_conn, mock_cur = _make_mock_conn()
        mock_get_conn.return_value = mock_conn

        from app.ingest_fs import ingest_single_file
        result = ingest_single_file(test_file, "demo")

    mock_extract.assert_called_once()
    mock_save.assert_not_called()
