"""FastAPI application — REST API + static frontend.

Routes are grouped under /api so the catch-all SPA fallback at / can serve
the React build for any other path.

Lifespan:
  - startup: init schema, kick off a catch-up sync in a background thread
    (non-blocking so the server accepts traffic immediately), start the
    APScheduler daily job.
  - shutdown: stop the scheduler.
"""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from fonliman import db, sync
from fonliman.config import STATIC_DIR
from fonliman.tefas import ALLOCATION_LABELS, TefasClient, TefasError

log = logging.getLogger("fonliman")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

_tefas = TefasClient()

# Listing endpoint returns ~300 KB of data and is hit by every "preview a
# fund code" UI action. A short in-memory cache keeps the modal snappy
# without staleness mattering — the listing only changes daily.
_LISTING_TTL_SECONDS = 600
_listing_cache: dict[str, Any] = {"at": 0.0, "data": None}


def _cached_listing() -> list:
    import time
    now = time.monotonic()
    if _listing_cache["data"] is None or now - _listing_cache["at"] > _LISTING_TTL_SECONDS:
        try:
            _listing_cache["data"] = _tefas.list_funds()
            _listing_cache["at"] = now
        except TefasError:
            return _listing_cache["data"] or []
    return _listing_cache["data"]


# ---------------------------------------------------------------------------
# Lifespan.
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001 — FastAPI signature requirement
    db.init_schema()
    log.info("schema initialised at %s", db.DB_PATH)

    # Catch-up sync in a daemon thread — doesn't block FastAPI startup.
    # If the user just opened a stale Docker container after days of sleep,
    # the dashboard renders immediately and data backfills behind the scenes.
    def _catchup():
        try:
            result = sync.run_sync(trigger="startup")
            log.info("startup sync done: %s", result)
        except Exception:
            log.exception("startup sync failed")

    threading.Thread(target=_catchup, daemon=True, name="startup-sync").start()
    sync.start_scheduler()

    yield

    sync.stop_scheduler()


app = FastAPI(
    title="fonliman",
    version="0.1.0",
    description="Self-hosted TEFAS fund dashboard.",
    lifespan=lifespan,
)

# CORS is permissive: the only client is the bundled frontend, but during
# local dev users may run Vite on :5173 while the API runs on :8765.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models for request/response shapes.
# ---------------------------------------------------------------------------


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    color: str = "#6b7280"
    target_pct: float | None = None


class GroupUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    target_pct: float | None = None
    sort_order: int | None = None
    # Sentinel that lets the client clear target_pct explicitly.
    clear_target_pct: bool = False


class FundCreate(BaseModel):
    code: str = Field(min_length=2, max_length=8)
    group_id: int | None = None


class FundUpdate(BaseModel):
    group_id: int | None = None


# ---------------------------------------------------------------------------
# Health / sync state.
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "last_sync": db.last_sync(),
        "fund_count": len(db.list_funds()),
        "group_count": len(db.list_groups()),
    }


@app.post("/api/refresh")
def manual_refresh() -> dict[str, Any]:
    """Fire-and-forget manual sync. Returns immediately; UI polls /api/health
    for the updated ``last_sync.finished_at`` timestamp.
    """
    threading.Thread(
        target=lambda: sync.run_sync(trigger="manual", force=True),
        daemon=True,
        name="manual-sync",
    ).start()
    return {"status": "started"}


# ---------------------------------------------------------------------------
# Groups.
# ---------------------------------------------------------------------------


@app.get("/api/groups")
def get_groups() -> list[dict[str, Any]]:
    return db.list_groups()


@app.post("/api/groups", status_code=201)
def post_group(payload: GroupCreate) -> dict[str, Any]:
    return db.create_group(payload.name, payload.color, payload.target_pct)


@app.patch("/api/groups/{group_id}")
def patch_group(group_id: int, payload: GroupUpdate) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if payload.name is not None:
        kwargs["name"] = payload.name
    if payload.color is not None:
        kwargs["color"] = payload.color
    if payload.clear_target_pct:
        kwargs["target_pct"] = None
    elif payload.target_pct is not None:
        kwargs["target_pct"] = payload.target_pct
    if payload.sort_order is not None:
        kwargs["sort_order"] = payload.sort_order
    updated = db.update_group(group_id, **kwargs)
    if updated is None:
        raise HTTPException(status_code=404, detail="group not found")
    return updated


@app.delete("/api/groups/{group_id}", status_code=204)
def delete_group_route(group_id: int) -> None:
    ok = db.delete_group(group_id)
    if not ok:
        raise HTTPException(status_code=404, detail="group not found")


# ---------------------------------------------------------------------------
# Funds.
# ---------------------------------------------------------------------------


@app.get("/api/funds/preview/{code}")
def preview_fund(code: str) -> dict[str, Any]:
    """Validate a fund code, used by the "+ Fon ekle" modal.

    Looks up the code in the cached listing (300 KB, hit by every preview
    UI action) rather than calling the rate-limited per-fund endpoint. This
    means the preview is essentially free even when the user adds several
    funds in quick succession — only the actual ``POST /api/funds`` will
    do a TEFAS round-trip, via the background backfill thread.
    """
    code_up = code.upper()
    listings = _cached_listing()
    listing = next((f for f in listings if f.code == code_up), None)
    if listing is None:
        raise HTTPException(status_code=404, detail="fund not found on TEFAS")
    return {
        "code": listing.code,
        "name": listing.name,
        "latest_date": None,  # filled by post_fund / dashboard after backfill
        "latest_price": None,
        "investor_count": None,
        "aum": None,
        "tefas_category": listing.fund_type,
        "risk_score": listing.risk_score,
        "return_1m": listing.return_1m,
        "return_1y": listing.return_1y,
    }


@app.get("/api/funds")
def get_funds() -> list[dict[str, Any]]:
    return db.list_funds()


@app.post("/api/funds", status_code=201)
def post_fund(payload: FundCreate) -> dict[str, Any]:
    code = payload.code.upper().strip()
    listings = _cached_listing()
    listing = next((f for f in listings if f.code == code), None)
    if listing is None:
        raise HTTPException(status_code=400, detail="fund code not recognised by TEFAS")
    fund = db.upsert_fund(
        code=code,
        name=listing.name,
        tefas_category=listing.fund_type,
        risk_score=listing.risk_score,
        group_id=payload.group_id,
    )
    # Kick off the per-fund backfill in the background — the UI shows a
    # loading state and polls /api/dashboard until rows appear.
    threading.Thread(
        target=lambda: sync.sync_single_fund(code),
        daemon=True,
        name=f"backfill-{code}",
    ).start()
    return fund


@app.patch("/api/funds/{code}")
def patch_fund(code: str, payload: FundUpdate) -> dict[str, Any]:
    ok = db.update_fund_group(code, payload.group_id)
    if not ok:
        raise HTTPException(status_code=404, detail="fund not found")
    return db.get_fund(code)  # type: ignore[return-value]


@app.delete("/api/funds/{code}", status_code=204)
def delete_fund_route(code: str) -> None:
    ok = db.delete_fund(code)
    if not ok:
        raise HTTPException(status_code=404, detail="fund not found")


# ---------------------------------------------------------------------------
# Dashboard — joined view for the main screen.
# ---------------------------------------------------------------------------


@app.get("/api/dashboard")
def get_dashboard() -> dict[str, Any]:
    """One-call payload for the home view: groups, their funds, latest NAVs,
    return windows, category rank, and 90-day sparkline points."""
    groups = db.list_groups()
    funds = db.list_funds()
    by_group: dict[int | None, list[dict[str, Any]]] = {}
    for f in funds:
        nav = db.nav_history(f["code"], days=90)
        rank = db.rank_history(f["code"], days=1)
        latest_nav = nav[-1] if nav else None
        prev_nav = nav[-2] if len(nav) >= 2 else None
        returns = db.returns_snapshot(f["code"]) or {}
        # Daily return computed from the last two NAVs we have on hand — the
        # listing endpoint's getiri1a is "1 month" not "1 day", so we derive.
        daily_pct = None
        if latest_nav and prev_nav and prev_nav["price"]:
            daily_pct = ((latest_nav["price"] - prev_nav["price"])
                         / prev_nav["price"] * 100)
        by_group.setdefault(f["group_id"], []).append({
            "code": f["code"],
            "name": f["name"],
            "tefas_category": f["tefas_category"],
            "risk_score": f["risk_score"],
            "group_id": f["group_id"],
            "sort_order": f["sort_order"],
            "latest_date": latest_nav["date"] if latest_nav else None,
            "latest_price": latest_nav["price"] if latest_nav else None,
            "investor_count": latest_nav["investor_count"] if latest_nav else None,
            "aum": latest_nav["aum"] if latest_nav else None,
            "daily_return_pct": daily_pct,
            "return_1m": returns.get("return_1m"),
            "return_3m": returns.get("return_3m"),
            "return_6m": returns.get("return_6m"),
            "return_1y": returns.get("return_1y"),
            "return_3y": returns.get("return_3y"),
            "return_5y": returns.get("return_5y"),
            "return_ytd": returns.get("return_ytd"),
            "category_rank": rank[-1]["category_rank"] if rank else None,
            "category_total": rank[-1]["category_total"] if rank else None,
            "sparkline": [
                {"date": r["date"], "price": r["price"]} for r in nav
            ],
        })
    return {
        "groups": groups,
        "funds_by_group": {str(k) if k is not None else "ungrouped": v
                           for k, v in by_group.items()},
        "last_sync": db.last_sync(),
    }


@app.get("/api/funds/{code}/detail")
def get_fund_detail(code: str) -> dict[str, Any]:
    fund = db.get_fund(code)
    if fund is None:
        raise HTTPException(status_code=404, detail="fund not found")
    nav = db.nav_history(code, days=1000)
    rank = db.rank_history(code, days=1000)
    allocation = db.latest_allocation(code)
    returns = db.returns_snapshot(code)
    friendly_allocation = None
    if allocation:
        raw = allocation["allocations"]
        friendly: dict[str, float] = {}
        for k, v in raw.items():
            label = ALLOCATION_LABELS.get(k, k)
            friendly[label] = friendly.get(label, 0.0) + v
        friendly_allocation = {
            "date": allocation["date"],
            "items": [{"label": k, "pct": v} for k, v in
                      sorted(friendly.items(), key=lambda x: -x[1])],
        }
    return {
        "fund": fund,
        "returns": returns,
        "nav": nav,
        "rank": rank,
        "allocation": friendly_allocation,
    }


# ---------------------------------------------------------------------------
# Static frontend.
#
# The Dockerfile builds the React app into ``fonliman/static``. In a dev
# checkout that directory won't exist — falling through to a stub keeps
# `uvicorn fonliman.main:app` runnable for backend development.
# ---------------------------------------------------------------------------


_INDEX_FALLBACK_BODY = (
    "<html><body style='font-family:system-ui;padding:2rem'>"
    "<h1>fonliman backend</h1>"
    "<p>Frontend build not found at <code>{path}</code>.</p>"
    "<p>Run <code>npm run build</code> in <code>frontend/</code>, "
    "or visit the Vite dev server during development.</p>"
    "</body></html>"
)


if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC_DIR / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}")
    def spa_catch_all(full_path: str):  # noqa: ARG001 — path captured for routing
        # API routes are matched first by FastAPI; anything else falls here
        # and serves the SPA's index.html so React Router can resolve.
        index = STATIC_DIR / "index.html"
        return FileResponse(index)
else:
    @app.get("/{full_path:path}")
    def dev_stub(full_path: str):  # noqa: ARG001
        return JSONResponse(
            content={"error": "frontend not built"},
            status_code=404,
        )
