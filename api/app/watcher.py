"""RAG VE - Watcher service per monitoraggio automatico della inbox.

Usa watchdog.PollingObserver (obbligatorio su Docker+Windows: inotify non funziona).
Monitora /data/inbox/<kb_namespace>/<files> e gestisce:
- FileCreatedEvent → auto-ingest del file
- FileDeletedEvent → soft delete del documento nel DB
"""

import logging
import os
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from app.ingest_fs import get_conn, ingest_single_file

# Estensioni supportate per l'ingest automatico
SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".pdf"}

logger = logging.getLogger(__name__)


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v not in (None, "") else default


def soft_delete_document(source_path: str) -> None:
    """Soft-delete di un documento rimosso dal filesystem.

    Imposta is_deleted=TRUE e deleted_at=NOW() su documents.
    Elimina fisicamente i chunk associati (hard delete).

    Args:
        source_path: percorso posix del file eliminato (usato come source_uri nel DB).
    """
    conn = get_conn()
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            # Cerca il documento per source_uri (non ancora eliminato)
            cur.execute(
                "SELECT id::text FROM documents WHERE source_uri=%s AND (is_deleted=FALSE OR is_deleted IS NULL)",
                (source_path,),
            )
            row = cur.fetchone()
            if not row:
                logger.warning(f"Documento non trovato per soft delete: {source_path}")
                conn.rollback()
                return

            doc_id = row[0]

            # Soft delete: marca come eliminato
            cur.execute(
                "UPDATE documents SET is_deleted=TRUE, deleted_at=now(), updated_at=now() WHERE id=%s",
                (doc_id,),
            )

            # Hard delete dei chunk associati
            cur.execute("DELETE FROM chunks WHERE document_id=%s", (doc_id,))

        conn.commit()
        logger.info(f"Soft delete completato: {source_path} (doc_id: {doc_id})")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class InboxHandler(FileSystemEventHandler):
    """Handler eventi filesystem per la inbox dei documenti.

    Struttura attesa: /data/inbox/<kb_namespace>/<file>
    Il kb_namespace viene derivato dal nome della directory padre.
    """

    def __init__(self, inbox_root: str):
        self.inbox_root = Path(inbox_root)

    def on_created(self, event) -> None:
        """Gestisce la creazione di un nuovo file: avvia auto-ingest."""
        if event.is_directory:
            return

        fp = Path(event.src_path)
        if fp.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.debug(f"File ignorato (estensione non supportata): {fp}")
            return

        # Namespace KB = nome della directory padre rispetto a inbox_root
        kb_namespace = fp.parent.name
        logger.info(f"Nuovo file rilevato: {fp} (KB: {kb_namespace})")

        try:
            result = ingest_single_file(fp, kb_namespace)
            logger.info(
                f"Ingest completato: {fp.name} → "
                f"status={result.get('status')}, chunk={result.get('chunks_inserted', 0)}"
            )
        except Exception as e:
            logger.error(f"Errore durante l'ingest di {fp}: {e}")

    def on_deleted(self, event) -> None:
        """Gestisce la cancellazione di un file: soft delete nel DB."""
        if event.is_directory:
            return

        fp = Path(event.src_path)
        if fp.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return

        logger.info(f"File eliminato: {fp} — avvio soft delete")

        try:
            soft_delete_document(fp.as_posix())
        except Exception as e:
            logger.error(f"Errore durante il soft delete di {fp}: {e}")


class KBWatcher:
    """Servizio watcher per il monitoraggio automatico della inbox."""

    def __init__(self, inbox_root: str, poll_seconds: int = 30):
        self.inbox_root = inbox_root
        self.poll_seconds = poll_seconds
        self.observer: Optional[PollingObserver] = None

    def start(self) -> None:
        """Avvia il watcher con PollingObserver."""
        handler = InboxHandler(self.inbox_root)
        self.observer = PollingObserver(timeout=self.poll_seconds)
        self.observer.schedule(handler, self.inbox_root, recursive=True)
        self.observer.start()
        logger.info(
            f"Watcher avviato su {self.inbox_root} (polling ogni {self.poll_seconds}s)"
        )

    def stop(self) -> None:
        """Ferma il watcher in modo pulito."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Watcher fermato")

    def join(self) -> None:
        """Attende che il watcher termini (bloccante)."""
        if self.observer:
            self.observer.join()


def main() -> None:
    """Entry point del watcher service (avviato da Docker come app.watcher)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [watcher] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    inbox_root = _env("INBOX_ROOT", "/data/inbox")
    poll_seconds = int(_env("WATCHER_POLL_SECONDS", "30"))

    # Crea la directory inbox se non esiste ancora
    Path(inbox_root).mkdir(parents=True, exist_ok=True)

    watcher = KBWatcher(inbox_root, poll_seconds)

    try:
        watcher.start()
        logger.info(f"Watcher in ascolto su {inbox_root} — Ctrl+C per fermare")
        watcher.join()
    except KeyboardInterrupt:
        logger.info("Interruzione ricevuta, fermo il watcher...")
        watcher.stop()


if __name__ == "__main__":
    main()
