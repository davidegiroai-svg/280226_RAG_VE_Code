"""graph_query.py — M7 GraphRAG: traversal grafo entità + arricchimento sources.

Tutte le funzioni sono SYNC (psycopg2 cursor passato dall'esterno).
Usato sia negli endpoint API che nel query pipeline.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def get_document_entities(cur, doc_ids: list) -> list:
    """Ritorna tutte le entità associate ai document IDs forniti.

    Args:
        cur:     cursore psycopg2 aperto (RealDictCursor o standard)
        doc_ids: lista di UUID documento come stringhe

    Returns:
        Lista di dict: {id, doc_id, entity_type, canonical, display_name, raw_value, metadata}
        Lista vuota se doc_ids è vuota o nessuna entità trovata.
    """
    if not doc_ids:
        return []

    cur.execute(
        """
        SELECT
            id::text,
            doc_id::text,
            entity_type,
            canonical,
            display_name,
            raw_value,
            metadata
        FROM entities
        WHERE doc_id = ANY(%s::uuid[])
        ORDER BY entity_type, canonical
        """,
        (doc_ids,),
    )
    rows = cur.fetchall()
    # Supporta sia RealDictCursor (dict-like) che cursore standard (tuple)
    if not rows:
        return []
    first = rows[0]
    if hasattr(first, "keys"):
        return [dict(r) for r in rows]
    # tuple: mappa manualmente
    cols = ["id", "doc_id", "entity_type", "canonical", "display_name", "raw_value", "metadata"]
    return [dict(zip(cols, r)) for r in rows]


def traverse_related(cur, entity_ids: list, depth: int = 2) -> list:
    """Traversal ricorsivo del grafo da entity_ids seed fino a `depth` hop.

    Usa WITH RECURSIVE PostgreSQL CTE.
    Ritorna tutte le entità raggiungibili dai seed, inclusi i seed stessi.
    Depth è limitato a 5 per prevenire query fuori controllo.

    Args:
        cur:        cursore psycopg2 aperto
        entity_ids: UUID entità seed come stringhe
        depth:      profondità massima traversal (1-5, default 2)

    Returns:
        Lista di dict con chiave aggiuntiva 'depth' che indica i hop.
    """
    if not entity_ids:
        return []

    depth = min(int(depth), 5)

    cur.execute(
        """
        WITH RECURSIVE graph(id, entity_type, canonical, display_name, depth) AS (
            SELECT
                e.id,
                e.entity_type,
                e.canonical,
                e.display_name,
                0 AS depth
            FROM entities e
            WHERE e.id = ANY(%s::uuid[])

            UNION ALL

            SELECT
                e2.id,
                e2.entity_type,
                e2.canonical,
                e2.display_name,
                g.depth + 1
            FROM graph g
            JOIN entity_relations r ON (r.from_id = g.id OR r.to_id = g.id)
            JOIN entities e2 ON e2.id = CASE
                WHEN r.from_id = g.id THEN r.to_id
                ELSE r.from_id
            END
            WHERE g.depth < %s
        )
        SELECT
            id::text AS id,
            entity_type,
            canonical,
            display_name,
            MIN(depth) AS depth
        FROM graph
        GROUP BY id, entity_type, canonical, display_name
        ORDER BY MIN(depth), entity_type
        """,
        (entity_ids, depth),
    )
    rows = cur.fetchall()
    if not rows:
        return []
    first = rows[0]
    if hasattr(first, "keys"):
        return [dict(r) for r in rows]
    cols = ["id", "entity_type", "canonical", "display_name", "depth"]
    return [dict(zip(cols, r)) for r in rows]


def find_related_documents(cur, doc_ids: list, depth: int = 2) -> list:
    """Trova documenti collegati ai doc_ids via grafo entità condivise.

    Steps:
      1. Recupera entity_ids per i doc_ids forniti
      2. Traversa il grafo fino a `depth` hop
      3. Trova tutti i doc_ids che contengono quelle entità
      4. Esclude i doc_ids originali dai risultati

    Args:
        cur:     cursore psycopg2 aperto
        doc_ids: UUID documento di partenza
        depth:   profondità traversal grafo

    Returns:
        Lista di dict: {doc_id, source_uri, titolo, entity_count, shared_entities}
        ordinata per entity_count DESC.
    """
    if not doc_ids:
        return []

    # Step 1: entity IDs dei documenti sorgente
    seed_entities = get_document_entities(cur, doc_ids)
    if not seed_entities:
        return []

    seed_entity_ids = [e["id"] for e in seed_entities]

    # Step 2: traversal grafo
    all_entities = traverse_related(cur, seed_entity_ids, depth=depth)
    if not all_entities:
        return []

    all_entity_ids = [e["id"] for e in all_entities]

    # Step 3: documenti che contengono quelle entità, esclusi gli originali
    cur.execute(
        """
        SELECT
            e.doc_id::text,
            d.source_uri,
            d.titolo,
            COUNT(DISTINCT e.id) AS entity_count,
            array_agg(DISTINCT e.display_name ORDER BY e.display_name) AS shared_entities
        FROM entities e
        JOIN documents d ON d.id = e.doc_id
        WHERE e.id = ANY(%s::uuid[])
          AND e.doc_id <> ALL(%s::uuid[])
          AND d.is_deleted = false
        GROUP BY e.doc_id, d.source_uri, d.titolo
        ORDER BY entity_count DESC
        LIMIT 10
        """,
        (all_entity_ids, doc_ids),
    )
    rows = cur.fetchall()
    if not rows:
        return []
    first = rows[0]
    if hasattr(first, "keys"):
        return [dict(r) for r in rows]
    cols = ["doc_id", "source_uri", "titolo", "entity_count", "shared_entities"]
    return [dict(zip(cols, r)) for r in rows]


def enrich_sources(cur, sources: list, depth: int = 2) -> list:
    """Aggiunge 'related_entities' e 'related_docs' a ogni source dict.

    Non modifica sources in-place — ritorna nuova lista.
    Su qualsiasi errore DB ritorna sources invariato (graceful degradation).

    Nota: sources contengono 'id' = UUID del chunk, NON del documento.
    Esegue un batch lookup chunk→document_id prima del traversal.

    Args:
        cur:     cursore psycopg2 aperto
        sources: lista source dict da execute_search() (ogni dict ha 'id' = chunk UUID)
        depth:   profondità traversal grafo

    Returns:
        Nuova lista di source dict con chiavi aggiuntive:
          'related_entities': list[dict] — entità del documento del chunk
          'related_docs':     list[dict] — documenti correlati via grafo
    """
    if not sources:
        return []

    try:
        # Batch lookup: chunk_ids → document_ids
        chunk_ids = [s["id"] if isinstance(s, dict) else s.id for s in sources]
        cur.execute(
            """
            SELECT id::text AS chunk_id, document_id::text AS doc_id
            FROM chunks
            WHERE id = ANY(%s::uuid[])
            """,
            (chunk_ids,),
        )
        rows = cur.fetchall()
        if not rows:
            return list(sources)

        # Mappa chunk_id → doc_id
        first = rows[0]
        if hasattr(first, "keys"):
            chunk_to_doc = {r["chunk_id"]: r["doc_id"] for r in rows}
        else:
            chunk_to_doc = {r[0]: r[1] for r in rows}

        unique_doc_ids = list(set(chunk_to_doc.values()))

        # Entità per doc
        all_entities = get_document_entities(cur, unique_doc_ids)
        entities_by_doc: dict = {}
        for e in all_entities:
            entities_by_doc.setdefault(e["doc_id"], []).append(e)

        # Documenti correlati via grafo
        related_docs = find_related_documents(cur, unique_doc_ids, depth=depth)

        # Attach a ogni source
        enriched = []
        for s in sources:
            s_dict = dict(s) if isinstance(s, dict) else {
                "id": s.id, "score": s.score, "kb_namespace": s.kb_namespace,
                "source_path": s.source_path, "excerpt": s.excerpt,
            }
            chunk_id = s_dict["id"]
            doc_id = chunk_to_doc.get(chunk_id)
            s_dict["related_entities"] = entities_by_doc.get(doc_id, []) if doc_id else []
            s_dict["related_docs"] = related_docs
            enriched.append(s_dict)

        return enriched

    except Exception as e:
        logger.warning("enrich_sources: errore — %s", e)
        return list(sources)
