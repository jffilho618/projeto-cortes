"""Garante que .venv/bin (Linux) ou .venv/Scripts (Windows) esteja no PATH e isola o banco nos testes."""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(tempfile.gettempdir()) / 'picorte_pytest.db'}")

import picorte.config  # noqa: F401, E402
