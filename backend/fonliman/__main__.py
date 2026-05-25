"""``python -m fonliman`` entry point — runs uvicorn against the FastAPI app."""

from __future__ import annotations

import uvicorn

from fonliman.config import PORT


def main() -> None:
    uvicorn.run(
        "fonliman.main:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        # Reload only when explicitly requested via env — Docker production
        # runs need a stable process for the in-app scheduler to fire.
        reload=False,
    )


if __name__ == "__main__":
    main()
