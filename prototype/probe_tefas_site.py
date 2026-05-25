"""Probe whether the TEFAS fund detail page still exposes the data the
official API hides: investor count, AUM, portfolio allocation, top holdings.

If yes, we can scrape it for Faz 2. If no, Faz 2 needs an alternative source
(KAP filings, Foreks, etc.). Either way we want to know now, not later.
"""

from __future__ import annotations

import re

import requests

URL = "https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod=AOY"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}


def find_around(text: str, needle: str, window: int = 200) -> str:
    idx = text.lower().find(needle.lower())
    if idx < 0:
        return f"(not found: {needle})"
    start = max(0, idx - 40)
    return text[start : idx + window]


def main() -> None:
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    print(f"HTTP {resp.status_code}, {len(resp.text)} bytes")
    html = resp.text

    interesting = [
        "Yatırımcı Sayısı",
        "Pay Sayısı",
        "Fon Toplam Değeri",
        "Yönetim Ücreti",
        "Portföy Dağılımı",
        "Hisse Senedi",
        "Ters Repo",
        "Para Piyasası",
        "Risk Değeri",
    ]
    for needle in interesting:
        excerpt = find_around(html, needle, window=250)
        # Strip a lot of whitespace for readability.
        excerpt = re.sub(r"\s+", " ", excerpt).strip()
        print(f"\n--- {needle!r} ---")
        print(excerpt[:400])

    # Also try the JSON XHR endpoint TEFAS uses internally.
    print("\n" + "=" * 72)
    print("Internal XHR endpoint probe")
    print("=" * 72)
    api_url = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"
    payload = {
        "fontip": "YAT",
        "sfontur": "",
        "fonkod": "AOY",
        "fongrup": "",
        "bastarih": "21.05.2026",
        "bittarih": "23.05.2026",
        "fonturkod": "",
        "fonunvantip": "",
    }
    api_headers = HEADERS | {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.tefas.gov.tr",
        "Referer": URL,
    }
    r = requests.post(api_url, data=payload, headers=api_headers, timeout=20)
    print(f"BindHistoryInfo: HTTP {r.status_code}, {len(r.text)} bytes")
    try:
        j = r.json()
        print(f"keys: {list(j.keys())}")
        data = j.get("data") or []
        if data:
            print(f"first row keys: {list(data[0].keys())}")
            print(f"first row: {data[0]}")
    except Exception as e:  # noqa: BLE001
        print(f"json parse failed: {e}")
        print(r.text[:500])

    # And the allocation endpoint.
    api_url2 = "https://www.tefas.gov.tr/api/DB/BindHistoryAllocation"
    r2 = requests.post(api_url2, data=payload, headers=api_headers, timeout=20)
    print(f"\nBindHistoryAllocation: HTTP {r2.status_code}, {len(r2.text)} bytes")
    try:
        j2 = r2.json()
        print(f"keys: {list(j2.keys())}")
        data2 = j2.get("data") or []
        if data2:
            print(f"first row keys: {list(data2[0].keys())}")
            print(f"first row: {data2[0]}")
    except Exception as e:  # noqa: BLE001
        print(f"json parse failed: {e}")
        print(r2.text[:500])


if __name__ == "__main__":
    main()
