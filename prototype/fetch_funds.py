"""TEFAS data-fetch prototype.

Goal: validate that we can pull NAV history, fund metadata, and allocation
breakdown for a handful of sample fund codes. Print the shape and contents so
we can design the schema and UX from real data, not guesswork.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pprint import pformat

from tefas import Crawler

# Sample TEFAS codes picked to cover different allocation profiles (foreign
# equity, money market, gold, etc.) — substitute any TEFAS codes you want to
# probe. Not investment guidance, just convenient examples for testing.
CODES = ["AOY", "BDS", "PHE", "TP2", "YAY", "YZG"]

# TEFAS publishes the day's NAV in the evening. Today (Sun 2026-05-24) is a
# weekend, so the freshest expected data is Fri 2026-05-22. Pull 120 days for
# a healthy view including 1m / 3m windows.
END = date.today()
START = END - timedelta(days=120)


def banner(text: str) -> None:
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72)


def main() -> None:
    crawler = Crawler()

    banner("INFO TABLE — NAV + fund metadata (default columns)")
    for code in CODES:
        # No `columns` arg → return everything the info endpoint exposes.
        df = crawler.fetch(
            start=START.strftime("%Y-%m-%d"),
            end=END.strftime("%Y-%m-%d"),
            name=code,
        )
        print(f"\n--- {code} ---")
        if df.empty:
            print("  (no rows)")
            continue
        print(f"  columns: {list(df.columns)}")
        print(f"  rows:    {len(df)}")
        latest = df.sort_values("date").iloc[-1].to_dict()
        # Stringify dates/numpy types for readability.
        latest = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in latest.items()}
        print(f"  latest:  {pformat(latest, width=100, sort_dicts=False)}")

    banner("ALLOCATION TABLE — what the fund holds (kind='YAT', info='allocation')")
    # tefas-crawler exposes the allocation endpoint via kind argument. Try one.
    df_alloc = crawler.fetch(
        start=(END - timedelta(days=30)).strftime("%Y-%m-%d"),
        end=END.strftime("%Y-%m-%d"),
        name="AOY",
        kind="YAT",
    )
    print(f"\nAOY allocation rows: {len(df_alloc)}")
    if not df_alloc.empty:
        print(f"All columns: {list(df_alloc.columns)}")
        latest_alloc = df_alloc.sort_values("date").iloc[-1].to_dict()
        latest_alloc = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in latest_alloc.items()}
        print(f"Latest row:\n{pformat(latest_alloc, width=100, sort_dicts=False)}")

    banner("CATEGORY DISCOVERY — what categories do these 6 funds belong to?")
    # Look at the 'title' column and any category-like fields.
    for code in CODES:
        df = crawler.fetch(
            start=END.strftime("%Y-%m-%d"),
            end=END.strftime("%Y-%m-%d"),
            name=code,
        )
        if df.empty:
            # try yesterday too
            df = crawler.fetch(
                start=(END - timedelta(days=5)).strftime("%Y-%m-%d"),
                end=END.strftime("%Y-%m-%d"),
                name=code,
            )
        if df.empty:
            print(f"  {code}: no recent data")
            continue
        row = df.sort_values("date").iloc[-1]
        print(f"  {code}: title='{row.get('title', '?')}'  price={row.get('price', '?')}  date={row.get('date', '?')}")


if __name__ == "__main__":
    main()
