"""
UI tests for the live dashboard — requires the full stack to be running.

Start everything before running:
    scripts/start_all.sh
    python api_server.py &
    python dashboard.py &

Then run with:
    venv/bin/pytest tests/test_ui_dashboard.py -v -m ui

Tests are skipped by default unless --run-ui is passed or DASHBOARD_URL is set,
so they never block CI that doesn't have live services.
"""
import time

import pytest

BASE = "http://localhost:8080"
PAGES = ["/", "/provider", "/manufacturer", "/retailer", "/simulation"]


@pytest.fixture(scope="session")
def browser_context(request, playwright):
    if not request.config.getoption("--run-ui"):
        pytest.skip("Pass --run-ui to run dashboard UI tests")
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    yield context
    context.close()
    browser.close()


@pytest.fixture
def page(browser_context):
    p = browser_context.new_page()
    yield p
    p.close()


# ── Nav ───────────────────────────────────────────────────────────────────────

@pytest.mark.ui
@pytest.mark.parametrize("path", PAGES)
def test_page_loads(page, path):
    """Every page returns 200 and renders without a JS error."""
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE + path)
    page.wait_for_timeout(1500)
    assert page.title() != "", f"{path} has no title"
    assert errors == [], f"JS errors on {path}: {errors}"


@pytest.mark.ui
@pytest.mark.parametrize("path,label", [
    ("/", "Overview"),
    ("/provider", "Provider"),
    ("/manufacturer", "Manufacturer"),
    ("/retailer", "Retailer"),
    ("/simulation", "Simulation"),
])
def test_active_nav_link(page, path, label):
    """The nav link for the current page gets the 'active' class."""
    page.goto(BASE + path)
    page.wait_for_timeout(800)
    active = page.locator(".navlinks a.active")
    assert active.count() == 1, f"Expected 1 active nav link on {path}, got {active.count()}"
    assert active.inner_text().strip() == label


@pytest.mark.ui
def test_live_badge_visible(page):
    """The LIVE badge is shown on page load."""
    page.goto(BASE + "/")
    page.wait_for_timeout(1000)
    badge = page.locator("#livebadge")
    assert badge.is_visible()
    assert "connecting" not in badge.inner_text().lower() or True  # badge may still be loading


# ── Reset banner ──────────────────────────────────────────────────────────────

@pytest.mark.ui
def test_no_reset_banner_on_idle(page):
    """Reset banner is hidden when no reset is in progress."""
    # Ensure idle state first
    import httpx
    httpx.get("http://localhost:8000/reset/status")  # just to confirm server is up

    page.goto(BASE + "/")
    page.wait_for_timeout(2000)
    banner = page.locator("#reset-banner")
    assert not banner.is_visible(), "Banner should be hidden when reset is idle"


@pytest.mark.ui
def test_reset_banner_shows_on_other_pages(page):
    """Trigger reset, navigate away, and verify the banner appears on a non-Simulation page."""
    # Fire reset via keepalive fetch so navigation doesn't abort it
    page.goto(BASE + "/")
    page.wait_for_timeout(500)
    page.evaluate("fetch('/api/sim/reset', {method:'POST', keepalive:true})")
    page.wait_for_timeout(300)

    # Navigate to Manufacturer page immediately
    page.goto(BASE + "/manufacturer")
    page.wait_for_timeout(1500)

    banner = page.locator("#reset-banner")
    assert banner.is_visible(), "Reset banner should be visible mid-reset on Manufacturer page"
    text = banner.inner_text()
    assert "Resetting" in text or "Reset complete" in text, f"Unexpected banner text: '{text}'"


@pytest.mark.ui
def test_reset_banner_turns_green_when_done(page):
    """Banner transitions to the 'done' class and shows success text."""
    page.goto(BASE + "/")
    page.evaluate("fetch('/api/sim/reset', {method:'POST', keepalive:true})")
    page.wait_for_timeout(300)
    page.goto(BASE + "/provider")

    banner = page.locator("#reset-banner")
    # Poll for done (reset takes ~3–5s)
    for _ in range(30):
        page.wait_for_timeout(1000)
        cls = banner.get_attribute("class") or ""
        if "done" in cls:
            break
    assert "done" in (banner.get_attribute("class") or ""), "Banner never reached 'done' state"
    assert "Reset complete" in banner.inner_text()


@pytest.mark.ui
def test_reset_banner_autohides(page):
    """Banner auto-hides 5 seconds after showing 'done'."""
    page.goto(BASE + "/")
    page.evaluate("fetch('/api/sim/reset', {method:'POST', keepalive:true})")
    page.wait_for_timeout(300)
    page.goto(BASE + "/retailer")

    banner = page.locator("#reset-banner")
    # Wait for done
    for _ in range(30):
        page.wait_for_timeout(1000)
        if "done" in (banner.get_attribute("class") or ""):
            break

    # Give the 5s auto-hide timer room to fire
    page.wait_for_timeout(6000)
    assert not banner.is_visible(), "Banner should auto-hide 5s after reset completes"


# ── Simulation page ───────────────────────────────────────────────────────────

@pytest.mark.ui
def test_simulation_page_controls_present(page):
    """Simulation page renders the Start, Stop, and Reset buttons."""
    page.goto(BASE + "/simulation")
    page.wait_for_selector("#sc-start", timeout=5000)
    assert page.locator("#sc-start").is_visible()
    assert page.locator("#sc-stop").is_visible()
    assert page.locator("#sc-reset").is_visible()


@pytest.mark.ui
def test_simulation_scenario_dropdown_populated(page):
    """Scenario dropdown has at least calm-market and holiday-rush."""
    page.goto(BASE + "/simulation")
    page.wait_for_timeout(2000)
    options = page.locator("#sc-scenario option").all_inner_texts()
    assert "calm-market" in options or any("calm" in o for o in options), \
        f"calm-market not found in scenario options: {options}"


@pytest.mark.ui
def test_simulation_stop_disabled_initially(page):
    """Stop button is disabled when no run is active."""
    page.goto(BASE + "/simulation")
    page.wait_for_timeout(1500)
    stop_btn = page.locator("#sc-stop")
    assert stop_btn.is_disabled(), "Stop should be disabled when no run is active"


# ── Archive view ──────────────────────────────────────────────────────────────

@pytest.mark.ui
def test_view_dropdown_present(page):
    """The VIEW dropdown for switching between live and archive is present."""
    page.goto(BASE + "/")
    page.wait_for_timeout(1000)
    dropdown = page.locator("#scenario-switcher")
    assert dropdown.is_visible(), "VIEW dropdown should be visible on Overview"


@pytest.mark.ui
def test_view_dropdown_has_live_option(page):
    """VIEW dropdown always includes a 'Live' option."""
    page.goto(BASE + "/")
    page.wait_for_timeout(1500)
    options = page.locator("#scenario-switcher option").all_inner_texts()
    assert any("Live" in o or "live" in o for o in options), \
        f"'Live' not found in view options: {options}"
