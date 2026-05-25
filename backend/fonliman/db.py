"""SQLite schema, connection helpers, and DAO.

One DB file at ``$FONLIMAN_DATA_DIR/fonliman.db`` (mounted as a Docker volume
in production). The schema is intentionally narrow: we store what TEFAS gives
us, no derived metrics. All return windows beyond raw NAV come from TEFAS's
own pre-computed listing snapshot — keeping derivation out of the DB means
we never have to backfill or recompute when the algorithm changes.

Idempotency: every "history" table uses (fund_code, date) as a composite
primary key with ``INSERT OR REPLACE`` upserts. Re-running a sync for the
same day is safe.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any, Iterator

from fonliman.config import DB_PATH
from fonliman.tefas import (
    FundDailyAllocation,
    FundDailyInfo,
    FundDailyRank,
    FundListing,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    color       TEXT    NOT NULL DEFAULT '#6b7280',
    target_pct  REAL,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS funds (
    code           TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    tefas_category TEXT,
    risk_score     INTEGER,
    group_id       INTEGER REFERENCES groups(id) ON DELETE SET NULL,
    sort_order     INTEGER NOT NULL DEFAULT 0,
    added_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_funds_group ON funds(group_id);

-- Daily NAV + per-fund metadata. The "info" tier — investor count and AUM
-- come from this table.
CREATE TABLE IF NOT EXISTS nav_history (
    fund_code      TEXT NOT NULL,
    date           DATE NOT NULL,
    price          REAL NOT NULL,
    investor_count INTEGER,
    aum            REAL,
    share_count    INTEGER,
    PRIMARY KEY (fund_code, date),
    FOREIGN KEY (fund_code) REFERENCES funds(code) ON DELETE CASCADE
);

-- Category rank time series. Separated from nav_history because the rank
-- endpoint is queried with a coarser look-back (months, not date ranges).
CREATE TABLE IF NOT EXISTS rank_history (
    fund_code      TEXT NOT NULL,
    date           DATE NOT NULL,
    category_rank  INTEGER,
    category_total INTEGER,
    PRIMARY KEY (fund_code, date),
    FOREIGN KEY (fund_code) REFERENCES funds(code) ON DELETE CASCADE
);

-- Latest pre-computed returns from TEFAS's listing endpoint. Each sync
-- overwrites the previous row keyed on (fund_code) — we don't need history
-- here because the same numbers are derivable from nav_history if needed.
CREATE TABLE IF NOT EXISTS returns_snapshot (
    fund_code      TEXT PRIMARY KEY,
    snapshot_date  DATE NOT NULL,
    return_1m      REAL,
    return_3m      REAL,
    return_6m      REAL,
    return_1y      REAL,
    return_3y      REAL,
    return_5y      REAL,
    return_ytd     REAL,
    risk_score     INTEGER,
    fund_type      TEXT,
    active         INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (fund_code) REFERENCES funds(code) ON DELETE CASCADE
);

-- Allocation snapshot: TEFAS returns ~58 asset class columns per fund per
-- day, mostly null. We persist non-null values as a JSON blob to keep the
-- schema stable as TEFAS adds or renames classes. UI maps codes to friendly
-- labels at read time.
CREATE TABLE IF NOT EXISTS allocation_history (
    fund_code   TEXT NOT NULL,
    date        DATE NOT NULL,
    allocations TEXT NOT NULL,
    PRIMARY KEY (fund_code, date),
    FOREIGN KEY (fund_code) REFERENCES funds(code) ON DELETE CASCADE
);

-- Append-only log of sync attempts. Powers the "son güncelleme" badge in
-- the header and helps debug if something goes wrong.
CREATE TABLE IF NOT EXISTS sync_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at  TIMESTAMP,
    trigger      TEXT NOT NULL,
    status       TEXT,
    funds_synced INTEGER NOT NULL DEFAULT 0,
    error        TEXT
);
"""


# ---------------------------------------------------------------------------
# Connection plumbing.
# ---------------------------------------------------------------------------


def _make_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # `check_same_thread=False` is safe here: APScheduler runs sync jobs in a
    # background thread and FastAPI routes serve from another. Both go through
    # the @contextmanager `connection()` which opens fresh per call.
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # WAL gives us concurrent readers while a sync write is in flight — useful
    # when the user pokes around the dashboard during a manual refresh.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    """Yield a connection; commit on success, rollback on exception, close always."""
    conn = _make_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema() -> None:
    """Idempotent — safe to call on every startup."""
    with connection() as conn:
        conn.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Groups DAO.
# ---------------------------------------------------------------------------


def list_groups() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, name, color, target_pct, sort_order, created_at "
            "FROM groups ORDER BY sort_order, name"
        ).fetchall()
        return [dict(r) for r in rows]


def create_group(
    name: str,
    color: str = "#6b7280",
    target_pct: float | None = None,
) -> dict[str, Any]:
    with connection() as conn:
        # New groups get the next sort_order so they land at the end.
        nxt = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM groups"
        ).fetchone()["n"]
        cur = conn.execute(
            "INSERT INTO groups (name, color, target_pct, sort_order) "
            "VALUES (?, ?, ?, ?)",
            (name, color, target_pct, nxt),
        )
        gid = cur.lastrowid
        row = conn.execute(
            "SELECT id, name, color, target_pct, sort_order, created_at "
            "FROM groups WHERE id = ?",
            (gid,),
        ).fetchone()
        return dict(row)


_UNSET = object()  # sentinel: distinguishes "leave alone" from "set to NULL"


def update_group(
    group_id: int,
    *,
    name: str | None = None,
    color: str | None = None,
    target_pct: Any = _UNSET,
    sort_order: int | None = None,
) -> dict[str, Any] | None:
    fields: list[str] = []
    params: list[Any] = []
    if name is not None:
        fields.append("name = ?"); params.append(name)
    if color is not None:
        fields.append("color = ?"); params.append(color)
    if target_pct is not _UNSET:
        fields.append("target_pct = ?"); params.append(target_pct)
    if sort_order is not None:
        fields.append("sort_order = ?"); params.append(sort_order)
    if not fields:
        return None
    params.append(group_id)
    with connection() as conn:
        conn.execute(f"UPDATE groups SET {', '.join(fields)} WHERE id = ?", params)
        row = conn.execute(
            "SELECT id, name, color, target_pct, sort_order, created_at "
            "FROM groups WHERE id = ?",
            (group_id,),
        ).fetchone()
        return dict(row) if row else None


def delete_group(group_id: int) -> bool:
    with connection() as conn:
        cur = conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Funds DAO.
# ---------------------------------------------------------------------------


def list_funds() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT code, name, tefas_category, risk_score, group_id, "
            "       sort_order, added_at "
            "FROM funds ORDER BY sort_order, code"
        ).fetchall()
        return [dict(r) for r in rows]


def get_fund(code: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT code, name, tefas_category, risk_score, group_id, "
            "       sort_order, added_at "
            "FROM funds WHERE code = ?",
            (code.upper(),),
        ).fetchone()
        return dict(row) if row else None


def upsert_fund(
    code: str,
    name: str,
    tefas_category: str | None = None,
    risk_score: int | None = None,
    group_id: int | None = None,
) -> dict[str, Any]:
    code = code.upper()
    with connection() as conn:
        existing = conn.execute(
            "SELECT 1 FROM funds WHERE code = ?", (code,),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE funds SET name = ?, tefas_category = ?, risk_score = ?, "
                "       group_id = COALESCE(?, group_id) WHERE code = ?",
                (name, tefas_category, risk_score, group_id, code),
            )
        else:
            nxt = conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM funds"
            ).fetchone()["n"]
            conn.execute(
                "INSERT INTO funds (code, name, tefas_category, risk_score, "
                "                   group_id, sort_order) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (code, name, tefas_category, risk_score, group_id, nxt),
            )
        row = conn.execute(
            "SELECT code, name, tefas_category, risk_score, group_id, "
            "       sort_order, added_at "
            "FROM funds WHERE code = ?",
            (code,),
        ).fetchone()
        return dict(row)


def update_fund_group(code: str, group_id: int | None) -> bool:
    with connection() as conn:
        cur = conn.execute(
            "UPDATE funds SET group_id = ? WHERE code = ?",
            (group_id, code.upper()),
        )
        return cur.rowcount > 0


def delete_fund(code: str) -> bool:
    with connection() as conn:
        cur = conn.execute("DELETE FROM funds WHERE code = ?", (code.upper(),))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# History writes — called by the sync engine.
# ---------------------------------------------------------------------------


def upsert_nav_history_prices_only(rows: list[FundDailyInfo]) -> int:
    """Insert NAV rows preserving any existing investor_count/aum/share_count.

    Used when the price comes from the cheap (rate-tolerant) price-history
    endpoint, which doesn't carry investor/AUM data. We must not overwrite
    those columns with NULL — a previous full-info sync may have already
    populated them.
    """
    if not rows:
        return 0
    with connection() as conn:
        conn.executemany(
            "INSERT INTO nav_history (fund_code, date, price) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(fund_code, date) DO UPDATE SET price = excluded.price",
            [(r.code, r.date.isoformat(), r.price) for r in rows],
        )
        return len(rows)


def upsert_nav_history_full(rows: list[FundDailyInfo]) -> int:
    """Insert NAV rows including investor_count / AUM / share_count.

    Used for the recent-window sync from the rate-limited endpoint that
    actually carries these fields. Overwrites every column on conflict —
    by definition this caller has the most up-to-date info available.
    """
    if not rows:
        return 0
    with connection() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO nav_history "
            "(fund_code, date, price, investor_count, aum, share_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (r.code, r.date.isoformat(), r.price,
                 r.investor_count, r.aum, r.share_count)
                for r in rows
            ],
        )
        return len(rows)


def upsert_rank_history(rows: list[FundDailyRank]) -> int:
    if not rows:
        return 0
    with connection() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO rank_history "
            "(fund_code, date, category_rank, category_total) "
            "VALUES (?, ?, ?, ?)",
            [
                (r.code, r.date.isoformat(), r.category_rank, r.category_total)
                for r in rows
            ],
        )
        return len(rows)


def upsert_returns_snapshot(
    listings: list[FundListing], snapshot_date: date,
) -> int:
    """Upsert pre-computed returns, preserving any prior non-NULL columns
    when the new row has NULL there.

    TEFAS publishes new daily numbers in waves (Monday morning especially),
    so a fund's listing row can briefly have NULL returns mid-publish even
    though yesterday's numbers were valid. We don't want the UI to flicker
    to "—" for half a day, so we keep the last-good value via COALESCE.
    """
    if not listings:
        return 0
    with connection() as conn:
        tracked = {r["code"] for r in conn.execute(
            "SELECT code FROM funds"
        ).fetchall()}
        kept = [f for f in listings if f.code in tracked]
        conn.executemany(
            "INSERT INTO returns_snapshot "
            "(fund_code, snapshot_date, return_1m, return_3m, return_6m, "
            " return_1y, return_3y, return_5y, return_ytd, risk_score, "
            " fund_type, active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(fund_code) DO UPDATE SET "
            " snapshot_date = excluded.snapshot_date, "
            " return_1m = COALESCE(excluded.return_1m, returns_snapshot.return_1m), "
            " return_3m = COALESCE(excluded.return_3m, returns_snapshot.return_3m), "
            " return_6m = COALESCE(excluded.return_6m, returns_snapshot.return_6m), "
            " return_1y = COALESCE(excluded.return_1y, returns_snapshot.return_1y), "
            " return_3y = COALESCE(excluded.return_3y, returns_snapshot.return_3y), "
            " return_5y = COALESCE(excluded.return_5y, returns_snapshot.return_5y), "
            " return_ytd = COALESCE(excluded.return_ytd, returns_snapshot.return_ytd), "
            " risk_score = COALESCE(excluded.risk_score, returns_snapshot.risk_score), "
            " fund_type = COALESCE(excluded.fund_type, returns_snapshot.fund_type), "
            " active = excluded.active",
            [
                (f.code, snapshot_date.isoformat(),
                 f.return_1m, f.return_3m, f.return_6m,
                 f.return_1y, f.return_3y, f.return_5y, f.return_ytd,
                 f.risk_score, f.fund_type, int(f.active))
                for f in kept
            ],
        )
        return len(kept)


def upsert_allocation_history(rows: list[FundDailyAllocation]) -> int:
    if not rows:
        return 0
    with connection() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO allocation_history "
            "(fund_code, date, allocations) VALUES (?, ?, ?)",
            [
                (r.code, r.date.isoformat(), json.dumps(r.allocations))
                for r in rows
            ],
        )
        return len(rows)


# ---------------------------------------------------------------------------
# History reads — called by the API layer.
# ---------------------------------------------------------------------------


def latest_nav_dates() -> dict[str, date]:
    """Return {fund_code: max(date)} so the sync engine knows where to resume."""
    with connection() as conn:
        rows = conn.execute(
            "SELECT fund_code, MAX(date) AS d FROM nav_history GROUP BY fund_code"
        ).fetchall()
        return {r["fund_code"]: date.fromisoformat(r["d"]) for r in rows if r["d"]}


def nav_history(code: str, days: int = 90) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT date, price, investor_count, aum, share_count "
            "FROM nav_history WHERE fund_code = ? "
            "ORDER BY date DESC LIMIT ?",
            (code.upper(), days),
        ).fetchall()
        return [dict(r) for r in rows][::-1]


def rank_history(code: str, days: int = 90) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT date, category_rank, category_total "
            "FROM rank_history WHERE fund_code = ? "
            "ORDER BY date DESC LIMIT ?",
            (code.upper(), days),
        ).fetchall()
        return [dict(r) for r in rows][::-1]


def latest_allocation(code: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT date, allocations FROM allocation_history "
            "WHERE fund_code = ? ORDER BY date DESC LIMIT 1",
            (code.upper(),),
        ).fetchone()
        if not row:
            return None
        return {
            "date": row["date"],
            "allocations": json.loads(row["allocations"]),
        }


def returns_snapshot(code: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT snapshot_date, return_1m, return_3m, return_6m, "
            "       return_1y, return_3y, return_5y, return_ytd, "
            "       risk_score, fund_type, active "
            "FROM returns_snapshot WHERE fund_code = ?",
            (code.upper(),),
        ).fetchone()
        return dict(row) if row else None


def last_sync() -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT started_at, finished_at, trigger, status, "
            "       funds_synced, error "
            "FROM sync_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def record_sync_start(trigger: str) -> int:
    with connection() as conn:
        cur = conn.execute(
            "INSERT INTO sync_log (trigger, status) VALUES (?, 'running')",
            (trigger,),
        )
        return cur.lastrowid


def record_sync_end(
    sync_id: int,
    status: str,
    funds_synced: int,
    error: str | None = None,
) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE sync_log SET finished_at = ?, status = ?, "
            "       funds_synced = ?, error = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), status, funds_synced, error, sync_id),
        )


