# RAG VE API - Autenticazione tramite API key
"""Modulo autenticazione: API key con hash SHA-256 + dipendenza FastAPI.

Flusso:
1. Client invia header X-API-Key: <raw_key>
2. Il middleware calcola SHA-256 del raw key
3. Cerca key_hash nel DB, verifica is_active=TRUE ed expires_at > NOW() (o NULL)
4. Se valida: procede; altrimenti 401 (mancante) o 403 (invalida/revocata/scaduta)

Sicurezza:
- Il raw key NON viene mai salvato — solo il hash SHA-256
- AUTH_ENABLED=false disabilita l'auth (solo per sviluppo locale)
"""
import hashlib
import os

from fastapi import Header, HTTPException
from fastapi.security import APIKeyHeader

from .db import get_db_cursor

# Schema FastAPI per documentazione OpenAPI
_api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_api_key(key: str) -> str:
    """Calcola il hash SHA-256 di una API key raw.

    Args:
        key: la chiave raw in chiaro (mai salvare questo valore)

    Returns:
        Stringa esadecimale del hash SHA-256 (64 caratteri)
    """
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def verify_api_key(key_hash: str, cursor) -> bool:
    """Verifica che il hash di una API key sia presente e valida nel DB.

    Controlla:
    - key_hash esiste nella tabella api_keys
    - is_active = TRUE
    - expires_at IS NULL oppure expires_at > NOW()

    Args:
        key_hash: hash SHA-256 della key da verificare
        cursor: cursore psycopg2 aperto (RealDictCursor)

    Returns:
        True se la key è valida e attiva, False altrimenti
    """
    cursor.execute(
        """
        SELECT id FROM api_keys
        WHERE key_hash = %s
          AND is_active = TRUE
          AND (expires_at IS NULL OR expires_at > NOW())
        LIMIT 1
        """,
        (key_hash,),
    )
    return cursor.fetchone() is not None


def require_api_key(x_api_key: str = Header(default=None, alias="X-API-Key")):
    """Dipendenza FastAPI: verifica l'header X-API-Key su ogni richiesta.

    Se AUTH_ENABLED=false (env var), la verifica viene saltata.

    Raises:
        HTTPException 401: header X-API-Key mancante
        HTTPException 403: key invalida, revocata o scaduta
    """
    # Auth disabilitata in sviluppo
    if os.environ.get("AUTH_ENABLED", "true").lower() in ("false", "0", "no"):
        return

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Autenticazione richiesta. Inserire l'header X-API-Key.",
        )

    key_hash = hash_api_key(x_api_key)

    try:
        with get_db_cursor() as cursor:
            valid = verify_api_key(key_hash, cursor)
    except Exception:
        # In caso di errore DB durante verifica auth: deny per sicurezza
        raise HTTPException(
            status_code=503,
            detail="Errore di sistema durante la verifica dell'autenticazione.",
        )

    if not valid:
        raise HTTPException(
            status_code=403,
            detail="API key non valida, revocata o scaduta.",
        )
