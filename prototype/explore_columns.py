"""Discover what columns tefas-crawler v0.6.0 can return.

The default `fetch` call gave only date/code/title/price/category_rank/
category_total. The package supports a `columns` arg — let's see which extra
fields the TEFAS info endpoint exposes, plus what the allocation endpoint
returns. We're after: market_cap, investor_count, share_count, and the asset
breakdown (stock%, bond%, gold%, etc.).
"""

from __future__ import annotations

import inspect
from datetime import date, timedelta
from pprint import pformat

import tefas
from tefas import Crawler

# Inspect what the package itself exposes.
print("Package:", tefas.__file__)
print("Crawler.fetch signature:", inspect.signature(Crawler.fetch))
print("Crawler attrs:", [a for a in dir(Crawler) if not a.startswith("_")])
print()

# Look at the source of fetch and the schemas behind it.
try:
    from tefas.schema import InfoSchema, BreakdownSchema  # type: ignore[attr-defined]
    print("InfoSchema fields:", list(InfoSchema._declared_fields.keys()))
    print("BreakdownSchema fields:", list(BreakdownSchema._declared_fields.keys()))
except Exception as e:  # noqa: BLE001
    print(f"(schema import failed: {e})")

print()

# Try fetching with ALL columns and see what comes back.
crawler = Crawler()
end = date.today()
start = end - timedelta(days=10)

# 1) Info table — pass an extensive columns list.
print("=" * 72)
print("Info fetch with explicit columns")
print("=" * 72)
candidate_columns = [
    "code", "date", "title", "price",
    "market_cap", "number_of_shares", "number_of_investors",
    "category_rank", "category_total",
]
df = crawler.fetch(
    start=start.strftime("%Y-%m-%d"),
    end=end.strftime("%Y-%m-%d"),
    name="AOY",
    columns=candidate_columns,
)
print(f"AOY rows: {len(df)}, columns returned: {list(df.columns)}")
if not df.empty:
    print(pformat(df.sort_values("date").iloc[-1].to_dict(), width=100, sort_dicts=False))

# 2) Allocation/Breakdown — different `kind` value? The TEFAS site has two
# tabs: "Genel Bilgi" (info) and "Portföy Dağılımı" (allocation).
print()
print("=" * 72)
print("Breakdown attempt — kind variations")
print("=" * 72)
for kind in ["YAT", "EMK"]:
    for cols in [None, ["code", "date", "title", "stock", "government_bond", "fx_payment_bills", "foreign_equity", "fund_basket", "precious_metals", "other"]]:
        try:
            df = crawler.fetch(
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                name="AOY",
                kind=kind,
                columns=cols,
            )
            print(f"\nkind={kind}  cols={'default' if cols is None else 'breakdown'}  rows={len(df)}  cols={list(df.columns)}")
        except Exception as e:  # noqa: BLE001
            print(f"\nkind={kind}  cols={cols!r}  ERROR: {e}")
