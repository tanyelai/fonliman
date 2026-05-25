"""Runtime configuration sourced from environment variables.

The app is meant to run as a single Docker container, so anything that varies
between users — port, data directory, sync time, TZ — is an env var with a
sane default. No config file to manage.
"""

from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# Port chosen for low collision risk against common local dev servers
# (3000, 5173, 8000, 8080). Users can override with `PORT`.
PORT: int = _env_int("PORT", 8765)

# SQLite location. Volume-mounted in Docker so data survives container
# replacement. Resolves to ./data/fonliman.db when run outside Docker.
DATA_DIR: Path = Path(os.environ.get("FONLIMAN_DATA_DIR", "./data")).resolve()
DB_PATH: Path = DATA_DIR / "fonliman.db"

# Frontend build directory — produced by `npm run build` in /frontend, copied
# next to the Python package by the Dockerfile. FastAPI serves it at /.
STATIC_DIR: Path = Path(os.environ.get(
    "FONLIMAN_STATIC_DIR",
    str(Path(__file__).parent / "static"),
)).resolve()

# Istanbul time governs everything user-facing: TEFAS publishes NAV on IST
# evenings, and BIST holidays follow Turkish calendar.
TZ = ZoneInfo("Europe/Istanbul")

# Scheduler fires daily at this local hour:minute (24h). 22:30 IST is safely
# after TEFAS's evening publish window (which typically finishes by 21:30).
SYNC_HOUR: int = _env_int("FONLIMAN_SYNC_HOUR", 22)
SYNC_MINUTE: int = _env_int("FONLIMAN_SYNC_MINUTE", 30)
