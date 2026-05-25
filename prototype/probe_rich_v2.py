"""Probe rich-data TEFAS endpoints with the correct payload shape (from pytefas):
- basTarih/bitTarih in YYYYMMDD format (NOT bastarih/bittarih or DD.MM.YYYY)
- basSira/bitSira pagination indices
- 28-day max window per request

If these return real data, we can build Faz 2/3 against TEFAS directly.
"""

from __future__ import annotations

from datetime import date, timedelta
from pprint import pformat

import requests

ROOT = "https://www.tefas.gov.tr"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": ROOT,
    "Referer": f"{ROOT}/tr/fon-detayli-analiz/AOY",
}
session = requests.Session()
session.headers.update(HEADERS)

end = date.today()
start = end - timedelta(days=14)  # 2-week window, under 28-day cap


def make_body(fund_code: str) -> dict:
    return {
        "fonTipi": "YAT",
        "fonKodu": fund_code,
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


def post(endpoint: str, body: dict, label: str) -> dict | None:
    r = session.post(f"{ROOT}{endpoint}", json=body, timeout=20)
    print(f"\n{'=' * 72}\n{label}\nHTTP {r.status_code}, {len(r.text)} bytes\n{'=' * 72}")
    if r.status_code != 200:
        print(r.text[:400])
        return None
    j = r.json()
    print(f"errorCode: {j.get('errorCode')}, errorMessage: {j.get('errorMessage')!r}")
    rows = j.get("resultList") or []
    print(f"row count: {len(rows)}, toplamSayi: {j.get('toplamSayi')}, toplamSayfa: {j.get('toplamSayfa')}")
    if rows:
        first = rows[0]
        print(f"\nfirst row — {len(first)} fields:")
        print(pformat(first, width=110, sort_dicts=True))
        if len(rows) > 1:
            print(f"\nlast row:")
            print(pformat(rows[-1], width=110, sort_dicts=True))
    return j


# 1) Info endpoint
post("/api/funds/fonGnlBlgSiraliGetir", make_body("AOY"), "fonGnlBlgSiraliGetir — AOY")

# 2) Allocation endpoint
post("/api/funds/dagilimSiraliGetirT", make_body("AOY"), "dagilimSiraliGetirT — AOY (allocation)")

# 3) Same call for a few more sample codes — just to confirm the response
# shape is consistent across funds with different allocation profiles.
for code in ["BDS", "PHE", "TP2", "YAY", "YZG"]:
    j = post("/api/funds/fonGnlBlgSiraliGetir", make_body(code), f"info — {code}")
    if j:
        rows = j.get("resultList") or []
        if rows:
            r = rows[-1]
            # Print only fields likely to be the "rich" data we want
            keys_of_interest = [k for k in r.keys() if any(
                hint in k.lower() for hint in (
                    "yatirim", "buyuk", "deger", "pay", "sayi", "fiyat", "tarih", "kod", "unvan"
                )
            )]
            slim = {k: r[k] for k in keys_of_interest}
            print(f"\n{code} latest (filtered to investor/AUM/share-like fields):")
            print(pformat(slim, width=110, sort_dicts=True))
