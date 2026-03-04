"""conftest.py — aggiunge /app alla sys.path per import 'app.*' nei test."""
import os
import sys
from pathlib import Path

import pytest

# Quando i test girano nel container (WORKDIR=/app), tests/ è montato in /app/tests/.
# Aggiungiamo la directory parent (/app) a sys.path così 'from app.xxx import ...' funziona.
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def disable_auth_by_default(monkeypatch):
    """Disabilita l'autenticazione per tutti i test per default.

    I test in test_auth.py che verificano il comportamento dell'auth
    sovrascrivono questa impostazione con monkeypatch.setenv("AUTH_ENABLED", "true").
    """
    monkeypatch.setenv("AUTH_ENABLED", "false")
