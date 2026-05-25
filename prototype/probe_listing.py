"""Probe the new TEFAS listing endpoint.

tefas-crawler hits `/api/funds/fonGetiriBazliBilgiGetir` to discover fund
codes, but it only consumes the `fonKodu` field. The endpoint likely returns
much more: return percentages for various periods, category info, possibly
AUM. Let's see exactly what it provides — that determines whether our schema
needs daily NAV history or can lean on TEFAS's pre-computed metrics.

Also test the detail page route at `/tr/fon-detayli-analiz/{code}` and a few
related JSON endpoints to find a source for investor count / AUM / allocation.
"""

from __future__ import annotations

import json
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


def post(endpoint: str, payload: dict) -> dict:
    r = session.post(f"{ROOT}{endpoint}", json=payload, timeout=20)
    print(f"\nPOST {endpoint}  →  HTTP {r.status_code}, {len(r.text)} bytes")
    if r.status_code != 200:
        print(r.text[:500])
        return {}
    return r.json()


def show(label: str, body: dict, sample: int = 1) -> None:
    print(f"\n--- {label} ---")
    if not body:
        print("(empty)")
        return
    print(f"top-level keys: {list(body.keys())}")
    result = body.get("resultList") or body.get("data") or []
    print(f"result count: {len(result)}")
    if result:
        first = result[0]
        print(f"first row keys ({len(first)}): {sorted(first.keys())}")
        for row in result[:sample]:
            print(pformat(row, width=110, sort_dicts=True))


# 1) Listing endpoint with full filter — see all fields per fund row.
body = post(
    "/api/funds/fonGetiriBazliBilgiGetir",
    {
        "dil": "TR",
        "fonTipi": "YAT",
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
    },
)
show("Listing endpoint (full fund list)", body, sample=3)

# Filter listing to our 6 funds (find them in the result, show what's there).
result = body.get("resultList") or []
our = [r for r in result if r.get("fonKodu") in {"AOY", "BDS", "PHE", "TP2", "YAY", "YZG"}]
print(f"\nOur 6 funds in listing: {len(our)} found")
for r in our:
    print(f"\n  {r.get('fonKodu')} — {r.get('fonUnvan', '?')}")
    print(f"    keys: {sorted(r.keys())}")
    print(f"    {pformat(r, width=110, sort_dicts=True)}")

# 2) Probe a few likely detail endpoints by name guessing.
guesses = [
    "/api/funds/fonGenelBilgiGetir",
    "/api/funds/fonDetayBilgiGetir",
    "/api/funds/fonPortfoyDagilimiGetir",
    "/api/funds/fonYatirimciSayisiGetir",
    "/api/funds/fonBuyuklukGetir",
    "/api/funds/fonGenelInfo",
    "/api/funds/fonDetay",
]
for endpoint in guesses:
    try:
        body = post(endpoint, {"fonKodu": "AOY", "dil": "TR"})
        if body:
            show(endpoint, body, sample=1)
    except Exception as e:
        print(f"\n{endpoint}  ERROR: {e}")
