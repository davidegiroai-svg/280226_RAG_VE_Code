#!/usr/bin/env python3
# RAG VE API - Script CLI per gestione API keys
"""Script CLI per creare, revocare e listare API keys.

Uso:
  python -m app.manage_keys create --name "app-frontend"
  python -m app.manage_keys revoke --key-id <uuid>
  python -m app.manage_keys list

NOTA SICUREZZA:
  - Il raw key viene mostrato UNA SOLA VOLTA alla creazione.
  - Nel DB viene salvato solo il hash SHA-256, mai la key raw.
  - Conservare la key generata in un secret manager o vault.
"""
import argparse
import sys
import uuid
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor

from .auth import hash_api_key
from .db import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


def _get_conn():
    """Apre connessione psycopg2 sync al DB."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME,
    )


def cmd_create(name: str, expires_at: str = None):
    """Crea una nuova API key e la salva nel DB (solo hash).

    Stampa la key raw a schermo — non viene mai più recuperabile.

    Args:
        name: nome descrittivo per la key (es. "app-frontend")
        expires_at: data scadenza ISO 8601 opzionale (es. "2027-01-01")
    """
    raw_key = str(uuid.uuid4())
    key_hash = hash_api_key(raw_key)

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if expires_at:
                cur.execute(
                    """
                    INSERT INTO api_keys (key_hash, name, expires_at)
                    VALUES (%s, %s, %s)
                    RETURNING id, name, created_at
                    """,
                    (key_hash, name, expires_at),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO api_keys (key_hash, name)
                    VALUES (%s, %s)
                    RETURNING id, name, created_at
                    """,
                    (key_hash, name),
                )
            row = cur.fetchone()
        conn.commit()
    finally:
        conn.close()

    print("=" * 60)
    print("API KEY CREATA — SALVA QUESTO VALORE ORA (non recuperabile)")
    print("=" * 60)
    print(f"ID:         {row['id']}")
    print(f"Nome:       {row['name']}")
    print(f"Creata il:  {row['created_at']}")
    print(f"Scadenza:   {expires_at or 'Mai'}")
    print(f"\nX-API-Key:  {raw_key}")
    print("=" * 60)
    print("Usa questo valore nell'header HTTP: X-API-Key: <valore>")


def cmd_revoke(key_id: str):
    """Revoca una API key per ID.

    Args:
        key_id: UUID della key da revocare (colonna id in api_keys)
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE api_keys
                SET is_active = FALSE, revoked_at = NOW()
                WHERE id = %s
                RETURNING id, name
                """,
                (key_id,),
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        conn.close()

    if row:
        print(f"Key revocata: ID={row['id']}, Nome={row['name']}")
    else:
        print(f"Nessuna key trovata con ID: {key_id}", file=sys.stderr)
        sys.exit(1)


def cmd_list():
    """Elenca tutte le API keys (mai mostrare key_hash)."""
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, created_at, expires_at, revoked_at, is_active
                FROM api_keys
                ORDER BY created_at DESC
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        print("Nessuna API key nel database.")
        return

    print(f"{'ID':<38} {'Nome':<20} {'Attiva':<7} {'Creata il':<25} {'Scadenza'}")
    print("-" * 110)
    for row in rows:
        attiva = "SI" if row["is_active"] else "NO"
        scadenza = str(row["expires_at"])[:19] if row["expires_at"] else "Mai"
        creata = str(row["created_at"])[:19]
        print(f"{str(row['id']):<38} {row['name']:<20} {attiva:<7} {creata:<25} {scadenza}")


def main():
    parser = argparse.ArgumentParser(
        description="Gestione API keys per RAG VE"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Sotto-comando create
    p_create = subparsers.add_parser("create", help="Crea una nuova API key")
    p_create.add_argument("--name", required=True, help="Nome descrittivo della key")
    p_create.add_argument(
        "--expires-at",
        default=None,
        help="Data scadenza ISO 8601 (es. 2027-01-01). Default: nessuna scadenza.",
    )

    # Sotto-comando revoke
    p_revoke = subparsers.add_parser("revoke", help="Revoca una API key per ID")
    p_revoke.add_argument("--key-id", required=True, help="UUID della key da revocare")

    # Sotto-comando list
    subparsers.add_parser("list", help="Elenca tutte le API keys")

    args = parser.parse_args()

    if args.command == "create":
        cmd_create(args.name, expires_at=args.expires_at)
    elif args.command == "revoke":
        cmd_revoke(args.key_id)
    elif args.command == "list":
        cmd_list()


if __name__ == "__main__":
    main()
