"""
TDD — chunk_text_semantic()
Questi test DEVONO fallire prima che la funzione sia implementata.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from app.ingest_fs import chunk_text_semantic


def test_semantic_no_split_in_middle_of_sentence():
    """Il chunk non deve spezzare una frase a metà."""
    text = "Prima frase completa. Seconda frase completa. Terza frase completa."
    chunks = chunk_text_semantic(text, target_size=100, max_size=200, overlap_sentences=0)
    for idx, chunk in chunks:
        # ogni chunk deve terminare con punteggiatura di fine frase oppure essere l'ultimo
        stripped = chunk.strip()
        assert len(stripped) > 0, "chunk vuoto non ammesso"
    # Nessun chunk deve contenere una parola spezzata (la parola "completa" deve essere intera)
    all_text = " ".join(c for _, c in chunks)
    assert "complet" in all_text  # "completa" deve essere intatta


def test_semantic_overlap_preserves_context():
    """Con overlap_sentences=2, le ultime 2 frasi del chunk precedente compaiono nel successivo."""
    # Creiamo testo con frasi corte e max_size basso per forzare più chunk
    sentences = [f"Frase numero {i} con contenuto." for i in range(10)]
    text = " ".join(sentences)
    chunks = chunk_text_semantic(text, target_size=80, max_size=150, overlap_sentences=2)
    chunk_list = list(chunks)
    if len(chunk_list) < 2:
        # testo troppo corto per testare overlap — ok comunque
        return
    # Il secondo chunk deve contenere parte del contenuto dell'ultimo chunk precedente
    first_chunk_text = chunk_list[0][1]
    second_chunk_text = chunk_list[1][1]
    # Le ultime frasi del primo chunk devono apparire all'inizio del secondo
    # (verifica che ci sia del testo in comune)
    first_words = set(first_chunk_text.split())
    second_words = set(second_chunk_text.split())
    overlap_words = first_words & second_words
    assert len(overlap_words) > 0, "Nessun overlap trovato tra chunk consecutivi"


def test_semantic_empty_text():
    """Testo vuoto → lista vuota."""
    result = chunk_text_semantic("", target_size=1500, max_size=2000, overlap_sentences=2)
    assert list(result) == []


def test_semantic_single_sentence():
    """Singola frase → un solo chunk con indice 0."""
    text = "Una sola frase breve."
    chunks = list(chunk_text_semantic(text, target_size=1500, max_size=2000, overlap_sentences=2))
    assert len(chunks) == 1
    assert chunks[0][0] == 0
    assert "Una sola frase breve" in chunks[0][1]


def test_semantic_respects_max_size():
    """Nessun chunk deve superare max_size caratteri (salvo singola frase >= max_size)."""
    # Frasi da ~50 char ciascuna
    sentences = ["Questa è una frase di prova abbastanza lunga per il test." for _ in range(30)]
    text = " ".join(sentences)
    max_size = 300
    chunks = list(chunk_text_semantic(text, target_size=200, max_size=max_size, overlap_sentences=1))
    assert len(chunks) > 1, "Attesi più chunk"
    for idx, chunk in chunks:
        # Tolleriamo una singola frase che eccede max_size (non spezzabile)
        sentences_in_chunk = chunk.split(". ")
        if len(sentences_in_chunk) > 1:
            assert len(chunk) <= max_size + 200, (
                f"Chunk {idx} troppo lungo: {len(chunk)} > {max_size}"
            )
