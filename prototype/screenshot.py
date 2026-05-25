"""Headless render of the running fonliman UI — used to eyeball the design
without me being able to see the user's actual browser."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "screens"
OUT.mkdir(exist_ok=True)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme, dark in [("light", False), ("dark", True)]:
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                device_scale_factor=2,
                color_scheme="dark" if dark else "light",
            )
            page = context.new_page()
            page.goto("http://localhost:8766/", wait_until="networkidle")
            page.wait_for_timeout(700)
            page.screenshot(path=str(OUT / f"dashboard-{theme}.png"))
            # Click into AOY to capture the detail view.
            page.goto("http://localhost:8766/fund/AOY", wait_until="networkidle")
            page.wait_for_timeout(1200)
            page.screenshot(path=str(OUT / f"detail-{theme}.png"), full_page=True)
            context.close()
        browser.close()
    for f in sorted(OUT.iterdir()):
        print(f)


if __name__ == "__main__":
    main()
