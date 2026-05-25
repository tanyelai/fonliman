"""TEFAS API client.

Talks to four public endpoints under https://www.tefas.gov.tr/api/funds/...
that the official tefas.gov.tr site itself uses. No auth required, no rate
limit advertised — but we keep requests modest (≤10 per daily sync) anyway.

Endpoints in use, discovered empirically (the legacy fundturkey.com.tr
BindHistory* endpoints were retired in May 2026):

  /api/funds/fonGetiriBazliBilgiGetir   — listing of ~1000 funds with
    pre-computed return windows (1m/3m/6m/1y/3y/5y/YTD), risk score, fund
    type. One call snapshots the whole TEFAS universe.

  /api/funds/fonFiyatBilgiGetir         — per-fund NAV history with
    category_rank/category_total. Lookback is fixed to one of {1,3,6,12,36,
    60} months — arbitrary date ranges aren't supported.

  /api/funds/fonGnlBlgSiraliGetir       — per-fund daily series with
    NAV + investor count + AUM + share count. Date range up to 28 days
    per call; longer windows must chunk.

  /api/funds/dagilimSiraliGetirT        — per-fund daily series with
    portfolio allocation across 58 asset class codes (hs=Hisse Senedi,
    tr=Ters Repo, vmtl=Vadeli Mevduat TL, etc.). Same 28-day limit.

The two `Sirali` endpoints actually return rows for ALL funds in the date
range, not just the requested one — so we filter client-side to keep
caller-facing API simple.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterator

import requests

log = logging.getLogger("fonliman.tefas")

ROOT = "https://www.tefas.gov.tr"

# Browser-shaped headers because the site checks for them. No api-key required.
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": ROOT,
    "Referer": f"{ROOT}/tr/fon-detayli-analiz",
}

# Each call to a "Sirali" endpoint may cover at most this many days.
SIRALI_MAX_WINDOW_DAYS = 28

# The price-history endpoint quantises look-back into these discrete months.
# Anything else returns "Sistem Hatası!!". 60 = 5 years, the API's hard cap.
VALID_PERIODS = (1, 3, 6, 12, 36, 60)


# ---------------------------------------------------------------------------
# Allocation field codes → friendly Turkish labels.
#
# TEFAS reports portfolio breakdown using 2-4 letter codes (hs, tr, vmtl…)
# rather than full names. The codes correspond to asset classes regulated
# by SPK. The mapping below is best-effort based on the live API output;
# unknown codes fall through to their raw key so we never silently drop
# data.
# ---------------------------------------------------------------------------
ALLOCATION_LABELS: dict[str, str] = {
    # Equities
    "hs": "Hisse Senedi",
    "yhs": "Yabancı Hisse Senedi",
    # Government and corporate debt
    "hb": "Hazine Bonosu",
    "dt": "Devlet Tahvili",
    "dot": "Diğer Tahvil",
    "ost": "Özel Sektör Tahvili",
    "osks": "Özel Sektör Kira Sertifikası",
    "ybkb": "Yabancı Borçlanma",
    "ybosb": "Yabancı Özel Sektör Borçlanma",
    # Repo & money market
    "tr": "Ters Repo",
    "r": "Repo",
    "t": "Takasbank Para Piyasası",
    # Time deposits
    "vmtl": "Vadeli Mevduat (TL)",
    "vmd": "Vadeli Mevduat (Döviz)",
    "vmau": "Vadeli Mevduat (Altın)",
    "vdm": "Vadeli İşlem ve Opsiyon",
    "vint": "Vadeli İşlem (Bekleyen)",
    "vm": "Vadeli Mevduat",
    # Precious metals
    "km": "Kıymetli Maden",
    "kmkba": "Kıymetli Maden (Külçe Altın)",
    "kmkks": "Kıymetli Maden (Kira Sertifikası)",
    "kmbyf": "Kıymetli Maden BYF",
    # Fund baskets
    "fb": "Fon Sepeti",
    "yyf": "Yabancı Yatırım Fonu",
    "byf": "Borsa Yatırım Fonu",
    "ybyf": "Yabancı Borsa Yatırım Fonu",
    # Lease certificates
    "kkstl": "Kira Sertifikası (TL)",
    "kksd": "Kira Sertifikası (Döviz)",
    "kksyd": "Kira Sertifikası (Yabancı)",
    "kks": "Kira Sertifikası",
    "kibd": "Kira İhraçlı Borçlanma",
    # Other
    "fkb": "Finansman Bonosu",
    "bb": "Banka Bonosu",
    "bpp": "Borsa Para Piyasası",
    "tpp": "Takasbank Para Piyasası",
    "d": "Diğer",
    "db": "Döviz Bazlı Diğer",
    "kh": "Katılma Hesabı",
    "khtl": "Katılma Hesabı (TL)",
    "khau": "Katılma Hesabı (Altın)",
    "khd": "Katılma Hesabı (Döviz)",
    "yba": "Yabancı Alacaklar",
    "btaa": "BIST Takas Aracılık",
    "btas": "BIST Takas",
    "kba": "Kamu Borçlanma Araçları",
    "eut": "Eurobond",
    "gas": "Gayrimenkul Sertifikası",
    "gsykb": "Girişim Sermayesi Yatırım Kuruluşları Borçlanma",
    "gsyy": "Girişim Sermayesi Yatırım Yatırımcı",
    "gykb": "Gayrimenkul Yatırım Kuruluşları Borçlanma",
    "gyy": "Gayrimenkul Yatırım Yatırımcı",
    "hs2": "Hisse Senedi (İkincil)",
    "osdb": "Özel Sektör Diğer Borçlanma",
    "ymk": "Yabancı Menkul Kıymet",
    "yhs2": "Yabancı Hisse Senedi (İkincil)",
    "oksyd": "Özel Kira Sertifikası Yabancı Döviz",
}

# Fields in the dagilim response that are NOT asset classes (metadata).
_ALLOCATION_META_KEYS = {"fonKodu", "fonUnvan", "tarih", "bilFiyat"}


# ---------------------------------------------------------------------------
# Typed result shapes.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FundListing:
    """One row of the listing endpoint — pre-computed returns + categorisation."""

    code: str
    name: str
    fund_type: str | None
    risk_score: int | None
    active: bool
    return_1m: float | None
    return_3m: float | None
    return_6m: float | None
    return_1y: float | None
    return_3y: float | None
    return_5y: float | None
    return_ytd: float | None


@dataclass(frozen=True)
class FundDailyInfo:
    """One day from fonGnlBlgSiraliGetir."""

    code: str
    name: str
    date: date
    price: float
    investor_count: int | None
    aum: float | None
    share_count: int | None


@dataclass(frozen=True)
class FundDailyRank:
    """One day from fonFiyatBilgiGetir — used solely for category rank."""

    code: str
    date: date
    price: float
    category_rank: int | None
    category_total: int | None


@dataclass(frozen=True)
class FundDailyAllocation:
    """One day of asset class percentages. `allocations` keyed by raw API codes;
    use `friendly_allocations` for human-readable labels."""

    code: str
    date: date
    allocations: dict[str, float]  # raw codes → percentage

    @property
    def friendly_allocations(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for code, pct in self.allocations.items():
            label = ALLOCATION_LABELS.get(code, code)
            out[label] = out.get(label, 0.0) + pct
        return out


# ---------------------------------------------------------------------------
# Client.
# ---------------------------------------------------------------------------


class TefasError(RuntimeError):
    """Raised when TEFAS returns errorCode != null or HTTP ≥ 400."""


class TefasClient:
    """Thin facade over four TEFAS endpoints.

    TEFAS applies request-rate throttling that returns HTTP 429 with
    ``faultCode=ERR-224``. We've observed that bursts of small NAV requests
    are limited even though the total bandwidth is tiny — the rate is
    request-count based, not byte based. We mitigate by pacing requests
    (``min_request_interval``) and retrying 429s with backoff.
    """

    # Seconds to wait between successive requests. Empirically TEFAS tolerates
    # ~1 req/sec for the per-fund endpoints; we keep a small safety margin.
    DEFAULT_MIN_INTERVAL = 1.2

    # On 429 we wait this long, then this × 2, then × 4 before giving up.
    BACKOFF_BASE_SECONDS = 5.0
    MAX_RETRIES_ON_429 = 3

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        min_request_interval: float = DEFAULT_MIN_INTERVAL,
    ) -> None:
        self._timeout = timeout
        self._min_interval = min_request_interval
        self._last_call_ts: float = 0.0
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    # -- public API ----------------------------------------------------------

    def list_funds(self, kind: str = "YAT") -> list[FundListing]:
        """Snapshot every fund's pre-computed return windows + risk + category.

        ``kind`` selects the TEFAS fund family: YAT (mutual fund), EMK
        (pension), BYF (ETF). Default is YAT which covers everything the user
        sees on the regular fund-analysis page.
        """
        payload = {
            "dil": "TR",
            "fonTipi": kind,
            "kurucuKodu": None,
            "sfonTurKod": None,
            "fonTurAciklama": None,
            "islem": 1,
            "fonTurKod": None,
            "fonGrubu": None,
            "donemGetiri1a": "1",
            "donemGetiri3a": "1",
            "donemGetiri6a": "1",
            "donemGetiri1y": "1",
            "donemGetiriyb": "1",
            "donemGetiri3y": "1",
            "donemGetiri5y": "1",
            "basTarih": None,
            "bitTarih": None,
            "calismaTipi": 2,
            "getiriOrani": "1",
        }
        rows = self._post("/api/funds/fonGetiriBazliBilgiGetir", payload)
        return [_parse_listing_row(r) for r in rows]

    def fund_history_with_rank(self, code: str, months: int) -> list[FundDailyRank]:
        """Per-fund NAV history including category rank.

        Lookback is snapped to the nearest valid period ≥ requested months.
        """
        period = _snap_period(months)
        payload = {"fonKodu": code.upper(), "dil": "TR", "periyod": period}
        rows = self._post("/api/funds/fonFiyatBilgiGetir", payload)
        out = []
        for r in rows:
            try:
                price = float(r["fiyat"])
            except (KeyError, ValueError, TypeError):
                continue
            if price <= 0:
                # Mid-publish zero rows — see comment in fund_daily_info.
                continue
            try:
                out.append(FundDailyRank(
                    code=r["fonKodu"],
                    date=date.fromisoformat(r["tarih"][:10]),
                    price=price,
                    category_rank=_safe_int(r.get("kategoriDerece")),
                    category_total=_safe_int(r.get("kategoriFonSay")),
                ))
            except (KeyError, ValueError, TypeError):
                continue
        return out

    def fund_daily_info(
        self, code: str, start: date, end: date
    ) -> list[FundDailyInfo]:
        """NAV + investor count + AUM + share count, one row per trading day."""
        out: list[FundDailyInfo] = []
        for chunk_start, chunk_end in _chunk_dates(start, end, SIRALI_MAX_WINDOW_DAYS):
            payload = _sirali_payload(code, chunk_start, chunk_end)
            rows = self._post("/api/funds/fonGnlBlgSiraliGetir", payload)
            for r in rows:
                if r.get("fonKodu") != code.upper():
                    continue
                try:
                    price = float(r["fiyat"])
                except (KeyError, ValueError, TypeError):
                    continue
                # TEFAS sometimes returns mid-publish rows for the current
                # day with price=0 (and zeroed AUM/shares but populated
                # investor count). Reject — a NAV of zero is never a real
                # trade price; we'd rather wait for the real row to appear.
                if price <= 0:
                    continue
                try:
                    out.append(FundDailyInfo(
                        code=r["fonKodu"],
                        name=r.get("fonUnvan", ""),
                        date=date.fromisoformat(r["tarih"][:10]),
                        price=price,
                        investor_count=_safe_int(r.get("kisiSayisi")),
                        aum=_safe_float(r.get("portfoyBuyukluk")),
                        share_count=_safe_int(r.get("tedPaySayisi")),
                    ))
                except (KeyError, ValueError, TypeError):
                    continue
        # API returns newest first; canonicalise to ascending so callers don't
        # have to sort.
        out.sort(key=lambda x: x.date)
        return _dedupe_by_date(out)

    def fund_allocation(
        self, code: str, start: date, end: date
    ) -> list[FundDailyAllocation]:
        """Portfolio breakdown for one fund. Convenience wrapper around
        ``bulk_allocation`` — handy for ad-hoc use; sync paths should call
        ``bulk_allocation`` directly to avoid re-downloading 13MB per fund.
        """
        by_code = self.bulk_allocation(start, end, codes={code.upper()})
        return by_code.get(code.upper(), [])

    def bulk_allocation(
        self,
        start: date,
        end: date,
        codes: set[str] | None = None,
    ) -> dict[str, list[FundDailyAllocation]]:
        """Fetch allocation rows once and dispatch them by fund code.

        TEFAS's allocation endpoint ignores ``fonKodu`` and returns every fund
        in the date range — ~13 MB for a 14-day window. Calling it per-fund
        wastes bandwidth and time. ``codes`` filters which keys end up in the
        return dict; pass None to keep them all.
        """
        codes_upper = {c.upper() for c in codes} if codes else None
        bucket: dict[str, list[FundDailyAllocation]] = {}
        for chunk_start, chunk_end in _chunk_dates(start, end, SIRALI_MAX_WINDOW_DAYS):
            # fonKodu is sent for cache-key parity but the endpoint ignores it.
            payload = _sirali_payload("", chunk_start, chunk_end)
            payload["fonKodu"] = None
            rows = self._post("/api/funds/dagilimSiraliGetirT", payload)
            for r in rows:
                code = r.get("fonKodu")
                if not code:
                    continue
                if codes_upper is not None and code not in codes_upper:
                    continue
                try:
                    when = date.fromisoformat(r["tarih"][:10])
                except (KeyError, ValueError, TypeError):
                    continue
                allocs: dict[str, float] = {}
                for k, v in r.items():
                    if k in _ALLOCATION_META_KEYS or v is None:
                        continue
                    try:
                        f = float(v)
                    except (ValueError, TypeError):
                        continue
                    if f != 0.0:
                        allocs[k] = f
                bucket.setdefault(code, []).append(
                    FundDailyAllocation(code=code, date=when, allocations=allocs)
                )
        # Canonicalise: ascending, deduped.
        return {c: _dedupe_by_date(sorted(v, key=lambda r: r.date))
                for c, v in bucket.items()}

    def validate_code(self, code: str) -> FundDailyInfo | None:
        """Cheap existence check used when the user adds a fund via UI.

        Returns the most recent row if the code is valid, None otherwise.
        Uses a 14-day window so weekends/holidays don't produce false negatives.
        """
        today = date.today()
        rows = self.fund_daily_info(code, today - timedelta(days=14), today)
        return rows[-1] if rows else None

    # -- private -------------------------------------------------------------

    def _post(self, endpoint: str, payload: dict) -> list[dict]:
        for attempt in range(self.MAX_RETRIES_ON_429 + 1):
            self._respect_rate_limit()
            try:
                resp = self._session.post(
                    f"{ROOT}{endpoint}", json=payload, timeout=self._timeout,
                )
            except requests.RequestException as exc:
                raise TefasError(f"TEFAS request failed: {exc}") from exc
            self._last_call_ts = time.monotonic()

            if resp.status_code == 429:
                if attempt >= self.MAX_RETRIES_ON_429:
                    raise TefasError(
                        f"TEFAS {endpoint} 429 (throttled) after "
                        f"{attempt + 1} attempts"
                    )
                # Exponential backoff: 5s, 10s, 20s.
                wait = self.BACKOFF_BASE_SECONDS * (2 ** attempt)
                log.warning(
                    "TEFAS %s throttled (attempt %d), sleeping %.0fs",
                    endpoint, attempt + 1, wait,
                )
                time.sleep(wait)
                continue

            if resp.status_code >= 400:
                raise TefasError(
                    f"TEFAS {endpoint} returned HTTP {resp.status_code}: "
                    f"{resp.text[:200]}"
                )
            try:
                body = resp.json()
            except ValueError as exc:
                raise TefasError(
                    f"TEFAS returned non-JSON: {resp.text[:200]}"
                ) from exc
            err = body.get("errorCode")
            if err:
                raise TefasError(
                    f"TEFAS {endpoint} errorCode={err}: "
                    f"{body.get('errorMessage')}"
                )
            return body.get("resultList") or []
        # Unreachable — loop exits via return or raise.
        raise TefasError(f"TEFAS {endpoint} retry loop fell through")

    def _respect_rate_limit(self) -> None:
        if self._min_interval <= 0 or self._last_call_ts == 0.0:
            return
        elapsed = time.monotonic() - self._last_call_ts
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _parse_listing_row(r: dict[str, Any]) -> FundListing:
    r1m = _safe_float(r.get("getiri1a"))
    r3m = _safe_float(r.get("getiri3a"))
    r6m = _safe_float(r.get("getiri6a"))
    r1y = _safe_float(r.get("getiri1y"))
    r3y = _safe_float(r.get("getiri3y"))
    r5y = _safe_float(r.get("getiri5y"))
    rytd = _safe_float(r.get("getiriyb"))
    # TEFAS occasionally returns a row with every return at 0.0 (e.g. when
    # the day's data is mid-publish on Monday morning). A genuine all-flat
    # return is statistically impossible across this many windows, so we
    # treat the pattern as "no data" and surface None to the UI.
    primaries = [r1m, r3m, r6m, r1y, rytd]
    if all(v == 0.0 for v in primaries if v is not None) and any(v is not None for v in primaries):
        r1m = r3m = r6m = r1y = r3y = r5y = rytd = None
    return FundListing(
        code=r.get("fonKodu", ""),
        name=r.get("fonUnvan", ""),
        fund_type=r.get("fonTurAciklama"),
        risk_score=_safe_int(r.get("riskDegeri")),
        active=bool(r.get("tefasDurum")),
        return_1m=r1m,
        return_3m=r3m,
        return_6m=r6m,
        return_1y=r1y,
        return_3y=r3y,
        return_5y=r5y,
        return_ytd=rytd,
    )


def _sirali_payload(code: str, start: date, end: date) -> dict[str, Any]:
    """Body shape used by both fonGnlBlgSiraliGetir and dagilimSiraliGetirT."""
    return {
        "fonTipi": "YAT",
        "fonKodu": code.upper(),
        "aramaMetni": None,
        "fonTurKod": None,
        "fonGrubu": None,
        "sfonTurKod": None,
        "fonTurAciklama": None,
        "kurucuKod": None,
        "basTarih": start.strftime("%Y%m%d"),
        "bitTarih": end.strftime("%Y%m%d"),
        "basSira": 1,
        "bitSira": 100000,
        "dil": "TR",
        "sFonTurKod": "",
        "fonKod": "",
        "fonGrup": "",
        "fonUnvanTip": "",
    }


def _chunk_dates(
    start: date, end: date, window_days: int,
) -> Iterator[tuple[date, date]]:
    """Yield inclusive (start, end) pairs covering [start, end] in window_days."""
    if start > end:
        return
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=window_days - 1), end)
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


def _snap_period(months: int) -> int:
    """Map a requested look-back to one of TEFAS's accepted period values."""
    for period in VALID_PERIODS:
        if period >= months:
            return period
    return VALID_PERIODS[-1]


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _dedupe_by_date(rows: list) -> list:
    """Sirali endpoints sometimes return duplicate (code, date) rows when a
    chunk boundary overlaps. Keep the last occurrence."""
    seen: dict[date, Any] = {}
    for r in rows:
        seen[r.date] = r
    return sorted(seen.values(), key=lambda r: r.date)
