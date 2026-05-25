# syntax=docker/dockerfile:1.7
#
# Multi-stage build for fonliman:
#   1) frontend  — Node builds Vite/React into static assets.
#   2) runtime   — Python serves API + static assets from a single process.
#
# The final image is ~140 MB (python:3.13-slim base + a handful of pure-
# Python deps). No node binary in the final stage.

# ---------------------------------------------------------------------------
# Stage 1 — build the React frontend.
# ---------------------------------------------------------------------------
FROM node:20-alpine AS frontend

WORKDIR /app/frontend

# Cache npm install across rebuilds when package.json hasn't changed.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
# Override the Vite outDir to a path inside this stage; stage 2 copies it
# explicitly. This decouples the build from the surrounding source layout.
RUN npx vite build --outDir /build/static --emptyOutDir


# ---------------------------------------------------------------------------
# Stage 2 — Python runtime.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    FONLIMAN_DATA_DIR=/data \
    PORT=8765

WORKDIR /app

# Install Python deps from pyproject.toml. We don't need to install the
# fonliman package itself — running via `python -m fonliman` with PYTHONPATH
# avoids the build step entirely and keeps the layer small.
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir \
        "fastapi>=0.115" \
        "uvicorn[standard]>=0.32" \
        "apscheduler>=3.10" \
        "requests>=2.32" \
        "pydantic>=2.9" \
        "holidays>=0.58"

COPY backend/ ./backend/
# Bring built frontend assets next to the Python package so the FastAPI
# StaticFiles mount finds them at the expected location.
COPY --from=frontend /build/static/ ./backend/fonliman/static/

# Volume-mounted at runtime so the SQLite DB survives container replacement.
RUN mkdir -p "$FONLIMAN_DATA_DIR"
VOLUME ["/data"]

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen(f'http://localhost:{__import__(\"os\").environ.get(\"PORT\",\"8765\")}/api/health',timeout=3).status==200 else 1)"

ENV PYTHONPATH=/app/backend
CMD ["python", "-m", "fonliman"]
