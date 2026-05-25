"""Verify the rich-data TEFAS endpoints exist and return what pytefas claims.

pytefas docs say:
  - /api/funds/fonGnlBlgSiraliGetir  → price + investor_count + AUM + shares
  - /api/funds/dagilimSiraliGetirT   → 50+ asset-class breakdown

If these work, the user's full Faz 2 / Faz 3 vision is feasible against TEFAS
alone — no KAP / headless-browser / third-party data needed.
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
start = end - timedelta(days=10)
fmt = "%d.%m.%Y"


def post(endpoint: str, payload: dict, label: str) -> None:
    r = session.post(f"{ROOT}{endpoint}", json=payload, timeout=20)
    print(f"\n{'=' * 72}\n{label}\nPOST {endpoint}  →  HTTP {r.status_code}, {len(r.text)} bytes\n{'=' * 72}")
    if r.status_code != 200:
        print(r.text[:500])
        return
    j = r.json()
    print(f"top-level keys: {list(j.keys())}")
    rows = j.get("resultList") or j.get("data") or []
    print(f"row count: {len(rows)}")
    if rows:
        first = rows[0]
        print(f"first row keys ({len(first)}): {sorted(first.keys())}")
        print("first row:")
        print(pformat(first, width=110, sort_dicts=True))


# Try a few payload shapes — endpoint name suggests "Sirali" (ordered) so it
# may accept date range + filter. Date format on TEFAS forms is DD.MM.YYYY.
payloads_to_try = [
    {
        "label": "fonGnlBlgSiraliGetir — AOY, 10 days, ISO dates",
        "payload": {
            "dil": "TR",
            "fonTipi": "YAT",
            "fonKodu": "AOY",
            "bastarih": start.strftime("%Y-%m-%d"),
            "bittarih": end.strftime("%Y-%m-%d"),
        },
    },
    {
        "label": "fonGnlBlgSiraliGetir — AOY, 10 days, TR dates",
        "payload": {
            "dil": "TR",
            "fonTipi": "YAT",
            "fonKodu": "AOY",
            "bastarih": start.strftime(fmt),
            "bittarih": end.strftime(fmt),
        },
    },
    {
        "label": "fonGnlBlgSiraliGetir — minimal payload",
        "payload": {"fonKodu": "AOY", "dil": "TR"},
    },
]
for case in payloads_to_try:
    post("/api/funds/fonGnlBlgSiraliGetir", case["payload"], case["label"])

# Try the allocation endpoint similarly.
alloc_payloads = [
    {
        "label": "dagilimSiraliGetirT — AOY, 10 days, TR dates",
        "payload": {
            "dil": "TR",
            "fonTipi": "YAT",
            "fonKodu": "AOY",
            "bastarih": start.strftime(fmt),
            "bittarih": end.strftime(fmt),
        },
    },
    {
        "label": "dagilimSiraliGetirT — minimal payload",
        "payload": {"fonKodu": "AOY", "dil": "TR"},
    },
]
for case in alloc_payloads:
    post("/api/funds/dagilimSiraliGetirT", case["payload"], case["label"])
