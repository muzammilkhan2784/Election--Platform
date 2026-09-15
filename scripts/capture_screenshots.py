"""
Capture the screenshots used in the README.

    python scripts/capture_screenshots.py

Requires the stack to be running (docker compose up -d) and a loaded database.
Screenshots are regenerated rather than hand-taken so they never drift from
what the application actually looks like.

Playwright is a development dependency:
    pip install playwright && python -m playwright install chromium
"""
import os
import sys
import time

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
MEMBER = ("member@example.com", "password123")


def login(page, email, password):
    page.goto(f"{APP}/login.html", wait_until="networkidle")
    page.fill("#email", email)
    page.fill("#password", password)
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard.html", timeout=15000)
    page.wait_for_load_state("networkidle")


def shoot(page, name, full_page=False):
    path = os.path.join(OUT_DIR, f"{name}.png")
    page.screenshot(path=path, full_page=full_page)
    size = os.path.getsize(path) // 1024
    print(f"  {name+'.png':<28} {size:>5} KB")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page = ctx.new_page()

        # ── Sign in ───────────────────────────────────────────────────────────
        page.goto(f"{APP}/login.html", wait_until="networkidle")
        shoot(page, "01-login")

        # ── Admin dashboard ───────────────────────────────────────────────────
        login(page, *ADMIN)
        page.wait_for_selector("#elections-list article", timeout=15000)
        shoot(page, "02-dashboard-admin")

        # ── Results, with the tally bars ──────────────────────────────────────
        page.goto(f"{APP}/results.html?id=751", wait_until="networkidle")
        page.wait_for_selector("#office-results article", timeout=15000)
        shoot(page, "03-results")

        # ── Admin: paged, searchable roster ───────────────────────────────────
        page.goto(f"{APP}/admin.html?tab=users", wait_until="networkidle")
        page.wait_for_selector("#users-table-body tr", timeout=15000)
        shoot(page, "04-admin-users")

        # Same screen filtered, to show search working against 20k rows.
        page.fill("#users-search", "khoury")
        page.wait_for_timeout(1200)
        shoot(page, "05-admin-search")

        # ── Employee to society assignments ───────────────────────────────────
        page.goto(f"{APP}/admin.html?tab=assignments", wait_until="networkidle")
        page.wait_for_function(
            "document.querySelectorAll('#assign-employee option').length > 1",
            timeout=15000,
        )
        page.wait_for_timeout(500)
        shoot(page, "06-admin-assignments")

        # ── System-wide reporting ─────────────────────────────────────────────
        page.goto(f"{APP}/admin.html?tab=reports", wait_until="networkidle")
        page.wait_for_function(
            "document.querySelectorAll('#panel-reports tbody tr').length > 0",
            timeout=15000,
        )
        page.wait_for_timeout(800)
        shoot(page, "07-admin-reports")

        # ── Ballot, as a member ───────────────────────────────────────────────
        ctx2 = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page2 = ctx2.new_page()
        login(page2, *MEMBER)
        page2.goto(f"{APP}/ballot.html?id=2001", wait_until="networkidle")
        try:
            page2.wait_for_selector(".vote-option", timeout=10000)
            # Select a couple of options so the chosen state is visible.
            options = page2.query_selector_all(".vote-option")
            for opt in options[:1]:
                opt.click()
            page2.wait_for_timeout(400)
            shoot(page2, "08-ballot")
        except Exception as exc:
            print(f"  (skipped ballot: {exc})")
        ctx2.close()

        # ── Grafana ───────────────────────────────────────────────────────────
        gpage = ctx.new_page()
        gpage.goto(
            f"{GRAFANA}/d/election-pipeline/election-platform"
            "?from=now-15m&to=now&kiosk=1",
            wait_until="networkidle",
        )
        # Panels render asynchronously after the data query returns.
        gpage.wait_for_timeout(6000)
        shoot(gpage, "09-grafana")

        browser.close()

    print(f"\nWritten to {OUT_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.exit(f"capture failed: {exc}\nIs the stack running? docker compose up -d")
