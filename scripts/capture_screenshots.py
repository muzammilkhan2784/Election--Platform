"""
Regenerate the README screenshots.

    python scripts/capture_screenshots.py

Needs the stack running (docker compose up -d) with data loaded. Generating
these rather than taking them by hand means they can't drift from what the app
actually looks like after an interface change.

Playwright is a dev dependency:
    pip install -r requirements-dev.txt
    python -m playwright install chromium
"""
import os
import sys

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

APP = os.getenv("APP_URL", "http://localhost:3000")
GRAFANA = os.getenv("GRAFANA_URL", "http://localhost:3001")
OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "screenshots"
)
VIEWPORT = {"width": 1440, "height": 900}
ADMIN = ("admin@example.com", "password123")


def login(page, email, password):
    page.goto(f"{APP}/login.html", wait_until="networkidle")
    page.fill("#email", email)
    page.fill("#password", password)
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard.html", timeout=15000)
    page.wait_for_load_state("networkidle")


def shoot(page, name):
    path = os.path.join(OUT_DIR, f"{name}.png")
    page.screenshot(path=path)
    print(f"  {name + '.png':<24} {os.path.getsize(path) // 1024:>4} KB")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        # 2x scale so the images stay sharp on high-density screens.
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page = ctx.new_page()

        login(page, *ADMIN)

        # Results, showing the tally bars.
        page.goto(f"{APP}/results.html?id=751", wait_until="networkidle")
        page.wait_for_selector("#office-results article", timeout=15000)
        shoot(page, "03-results")

        # The roster, filtered, to show search working against 20k rows.
        page.goto(f"{APP}/admin.html?tab=users", wait_until="networkidle")
        page.wait_for_selector("#users-table-body tr", timeout=15000)
        page.fill("#users-search", "khoury")
        page.wait_for_timeout(1200)
        shoot(page, "05-admin-search")

        # Grafana. Run a load test first if the graphs should show traffic:
        #   python scripts/load_test.py --voters 500 --concurrency 30
        gpage = ctx.new_page()
        gpage.goto(
            f"{GRAFANA}/d/election-pipeline/election-platform?from=now-15m&to=now&kiosk=1",
            wait_until="networkidle",
        )
        gpage.wait_for_timeout(6000)  # panels render after their queries return
        shoot(gpage, "09-grafana")

        browser.close()

    print(f"\nWritten to {OUT_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.exit(f"capture failed: {exc}\nIs the stack running? docker compose up -d")
