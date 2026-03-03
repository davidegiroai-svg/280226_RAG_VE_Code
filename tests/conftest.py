"""conftest.py — aggiunge /app alla sys.path per import 'app.*' nei test."""
import sys
from pathlib import Path

# Quando i test girano nel container (WORKDIR=/app), tests/ è montato in /app/tests/.
# Aggiungiamo la directory parent (/app) a sys.path così 'from app.xxx import ...' funziona.
sys.path.insert(0, str(Path(__file__).parent.parent))
