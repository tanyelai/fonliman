"""Sync engine — pulls TEFAS data into the local SQLite DB.

Three trigger points, all routing to ``run_sync``:

  1. **Startup catch-up** (``run_sync(trigger="startup")``). Called once when
     FastAPI boots. For each tracked fund, looks at the latest date in
     ``nav_history`` and pulls forward from there. If the user's Mac was
     asleep for a week, the next open silently backfills the missing days.

  2. **Scheduled daily** (``run_sync(trigger="scheduled")``). APScheduler
     fires at the configured local time (default 22:30 IST). Skipped on
     BIST holidays — TEFAS doesn't publish new NAV for closed days, so
     hitting the API would either return stale or fail noisily.

  3. **Manual** (``run_sync(trigger="manual")``). Triggered by the
     ``POST /api/refresh`` endpoint when the user clicks the refresh icon
     in the dashboard header.

A single in-process lock prevents concurrent syncs (e.g. user clicks
refresh while scheduler fires). The latest run is always recorded in
``sync_log`` regardless of outcome.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import holidays
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from fonliman import db
from fonliman.config import SYNC_HOUR, SYNC_MINUTE, TZ
from fonliman.tefas import TefasClient, TefasError

log = logging.getLogger("fonliman.sync")

# Single global lock — sync touches every history table so two concurrent
# runs would race on UPSERTs. The lock is released as soon as one run
# finishes; manual refresh during a scheduled run waits ≤30s in practice.
_sync_lock = threading.Lock()

# Sync windows are tuned around two TEFAS realities:
#   1. The NAV-rich endpoint (fonGnlBlgSiraliGetir) is request-rate-throttled
#      so we minimise calls to it — last 28 days, once per fund per sync.
#   2. The price-history endpoint (fonFiyatBilgiGetir) returns up to 5 years
#      in one call, so it's the right tool for the long sparkline window.
# Investor count / AUM history is therefore "rolling from install time" —
# the first 30 days of those metrics are backfilled on day one, and the
# series extends naturally as the app runs.
PRICE_HISTORY_MONTHS_INITIAL = 12
INFO_BACKFILL_DAYS = 28  # one Sirali chunk, no chunking needed
INITIAL_ALLOCATION_DAYS = 14


@dataclass(frozen=True)
class SyncResult:
    funds_synced: int
    rows_inserted: int
    skipped_reason: str | None = None


# ---------------------------------------------------------------------------
# Holiday awareness.
# ---------------------------------------------------------------------------


def _bist_closed(day: date) -> str | None:
    """Return a human reason if BIST is closed on ``day``, else None.

    BIST is closed on Turkish public + religious holidays and weekends.
    ``holidays.TR`` includes both national and religious days for the year
    requested. The library refreshes its movable-feast list each year so
    we don't need to maintain a static table.
    """
    if day.weekday() >= 5:  # 5=Sat, 6=Sun
        return "weekend"
    tr_hols = holidays.country_holidays("TR", years=[day.year])
    name = tr_hols.get(day)
    if name:
        return f"holiday: {name}"
    return None


def _today_ist() -> date:
    return datetime.now(TZ).date()


# ---------------------------------------------------------------------------
# Per-fund sync.
# ---------------------------------------------------------------------------


def _sync_price_rank(
    client: TefasClient, code: str, months: int,
) -> int:
    """Pull the price + category-rank series in one HTTP call.

    The endpoint covers up to 5 years (``months=60``) which is far cheaper
    than chunking the heavy NAV endpoint. Price written to ``nav_history``
    with NULL metadata columns; ``_sync_recent_info`` fills them for the
    last 30 days where they actually matter.
    """
    written = 0
    try:
        rows = client.fund_history_with_rank(code, months=months)
    except TefasError as exc:
        log.warning("fund_history_with_rank %s: %s", code, exc)
        return 0

    # Build the NAV inserts from price (no investor/AUM yet).
    from fonliman.tefas import FundDailyInfo  # local import avoids cycle at module top
    nav_rows = [
        FundDailyInfo(
            code=r.code, name="", date=r.date, price=r.price,
            investor_count=None, aum=None, share_count=None,
        )
        for r in rows
    ]
    written += db.upsert_nav_history_prices_only(nav_rows)
    written += db.upsert_rank_history(rows)
    return written


def _sync_recent_info(
    client: TefasClient, code: str, days: int,
) -> int:
    """Pull NAV + investor count + AUM + share count for the trailing window.

    This is the only place where the rate-limited ``fonGnlBlgSiraliGetir``
    endpoint runs. Window is short enough to fit in one HTTP request
    (TEFAS caps at 28 days per call).
    """
    today = _today_ist()
    since = today - timedelta(days=days)
    try:
        info_rows = client.fund_daily_info(code, since, today)
    except TefasError as exc:
        log.warning("fund_daily_info %s: %s", code, exc)
        return 0
    return db.upsert_nav_history_full(info_rows)


def _sync_bulk_allocation(
    client: TefasClient, codes: set[str], since: date, until: date,
) -> int:
    """One bulk fetch of allocation data, dispatched to all tracked funds."""
    if not codes:
        return 0
    try:
        by_code = client.bulk_allocation(since, until, codes=codes)
    except TefasError as exc:
        log.warning("bulk_allocation: %s", exc)
        return 0
    written = 0
    for code, rows in by_code.items():
        written += db.upsert_allocation_history(rows)
    return written


def _months_between(start: date, end: date) -> int:
    days = max(0, (end - start).days)
    return (days // 30) + 1


def _months_for_catchup(cursor: date | None, today: date) -> int:
    """Pick the smallest TEFAS-accepted period that covers our gap.

    Sized to one of the discrete values the price-history endpoint accepts
    ({1, 3, 6, 12, 36, 60}). A fresh fund gets a year; a daily catch-up
    asks for 1 month and is essentially a no-op on conflict.
    """
    if cursor is None:
        return PRICE_HISTORY_MONTHS_INITIAL
    gap_days = (today - cursor).days
    if gap_days <= 25:
        return 1
    if gap_days <= 80:
        return 3
    if gap_days <= 170:
        return 6
    return 12


# ---------------------------------------------------------------------------
# Whole-universe sync.
# ---------------------------------------------------------------------------


def _sync_listing_snapshot(
    client: TefasClient, snapshot_date: date,
) -> int:
    """One call: refresh pre-computed return windows + risk + fund type."""
    try:
        listings = client.list_funds()
    except TefasError as exc:
        log.warning("list_funds: %s", exc)
        return 0
    return db.upsert_returns_snapshot(listings, snapshot_date)


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------


def run_sync(
    trigger: str = "manual",
    *,
    force: bool = False,
    client: TefasClient | None = None,
) -> SyncResult:
    """Pull whatever's missing for every tracked fund.

    ``force=True`` bypasses the BIST-closed check — used by manual refresh
    so the user can re-pull a day's data on demand.
    """
    if not _sync_lock.acquire(blocking=False):
        return SyncResult(0, 0, skipped_reason="already running")

    sync_id = db.record_sync_start(trigger)
    funds_synced = 0
    rows_written = 0
    error: str | None = None

    try:
        today = _today_ist()
        closed = _bist_closed(today) if not force else None
        if closed and trigger == "scheduled":
            # Scheduled fire on a closed day → silently skip (no new data anyway).
            db.record_sync_end(sync_id, "skipped", 0, f"BIST {closed}")
            return SyncResult(0, 0, skipped_reason=closed)

        client = client or TefasClient()
        tracked = db.list_funds()
        latest = db.latest_nav_dates()
        codes = {f["code"] for f in tracked}

        # Listing snapshot — one HTTP call, every fund's pre-computed returns.
        rows_written += _sync_listing_snapshot(client, today)

        # Per-fund price + rank history. One HTTP call per fund covers
        # months of data, so we use the smallest period that catches us up.
        for f in tracked:
            code = f["code"]
            cursor = latest.get(code)
            months = _months_for_catchup(cursor, today)
            rows_written += _sync_price_rank(client, code, months=months)
            funds_synced += 1

        # Per-fund recent investor/AUM/share-count. Heavy on the rate limit
        # so we keep the window narrow and only ever one call per fund.
        for f in tracked:
            rows_written += _sync_recent_info(
                client, f["code"], days=INFO_BACKFILL_DAYS,
            )

        # Allocation — one bulk fetch across all tracked funds.
        alloc_since = today - timedelta(days=INITIAL_ALLOCATION_DAYS)
        rows_written += _sync_bulk_allocation(client, codes, alloc_since, today)

        db.record_sync_end(sync_id, "success", funds_synced)
        log.info(
            "sync %s ok: %d funds, %d rows written",
            trigger, funds_synced, rows_written,
        )
        return SyncResult(funds_synced, rows_written)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        log.exception("sync %s failed", trigger)
        db.record_sync_end(sync_id, "error", funds_synced, error)
        raise
    finally:
        _sync_lock.release()


def sync_single_fund(code: str) -> int:
    """Cheap sync when the user just added one fund via the UI.

    Hits only the two endpoints that don't have aggressive per-IP rate limits:
    the listing (so pre-computed returns are immediately visible) and the
    price-history endpoint (so the sparkline draws). Investor count, AUM,
    and allocation come on the next scheduled or manual full sync — by then
    TEFAS's throttle window has reset.

    Rationale: when the user pastes in 6 codes in quick succession we used
    to fire 6 simultaneous backfills, each calling the rate-limited NAV-rich
    endpoint. The first 2-3 succeeded; the rest got 429. By splitting the
    add-time path from the rich-data path we never trip the limiter just
    from UI clicks.
    """
    client = TefasClient()
    today = _today_ist()
    written = _sync_listing_snapshot(client, today)
    written += _sync_price_rank(client, code, months=PRICE_HISTORY_MONTHS_INITIAL)
    return written


# ---------------------------------------------------------------------------
# Scheduler wiring.
# ---------------------------------------------------------------------------


_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler:
    """Start an APScheduler that fires the daily sync. Idempotent."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    scheduler = BackgroundScheduler(timezone=TZ)
    scheduler.add_job(
        lambda: run_sync(trigger="scheduled"),
        CronTrigger(hour=SYNC_HOUR, minute=SYNC_MINUTE, timezone=TZ),
        id="daily-sync",
        # If the host was asleep at fire-time, APScheduler default is to
        # silently skip. That's fine — startup catch-up handles missed days.
        misfire_grace_time=3600,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    log.info("scheduler started: daily at %02d:%02d IST", SYNC_HOUR, SYNC_MINUTE)
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
