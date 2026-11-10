"""Part 1A demonstration in Edge (User Story 1, SC-001/SC-003; task T023)."""

import uuid

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import open_section

pytestmark = pytest.mark.e2e


def unique(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def send(page, client_id, tier, expected_rows):
    page.fill("#rl-client-id", client_id)
    page.select_option("#rl-tier", tier)
    page.click("#rl-send")
    # A locator assertion, not wait_for_function: string predicates are evaluated like eval()
    # and the portal's Content-Security-Policy (no 'unsafe-eval') correctly blocks them.
    expect(page.locator("#rl-history tr.history-row")).to_have_count(expected_rows)


def test_tier_table_lists_three_tiers(page):
    open_section(page, "part-1a")
    expect(page.locator("#rl-tiers tbody tr")).to_have_count(3)
    expect(page.locator("#rl-tiers")).to_contain_text("free")


def test_five_accepted_then_rejected_with_retry_after(page, expect_api_status):
    expect_api_status(429)
    open_section(page, "part-1a")
    page.click("#rl-reset")
    client_id = unique("e2e-free")
    for count in range(1, 7):
        send(page, client_id, "free", count)

    rows = page.locator("#rl-history tr.history-row")
    expect(rows.nth(0)).to_contain_text("REJECTED")
    expect(rows.nth(0)).to_contain_text("429")
    for index in range(1, 6):
        expect(rows.nth(index)).to_contain_text("ACCEPTED")
        expect(rows.nth(index)).to_contain_text("200")
    outcome = page.locator("#rl-last-outcome")
    expect(outcome).to_contain_text("REJECTED")
    expect(outcome).to_contain_text("Retry-After")


def test_tier_mismatch_warning(page):
    open_section(page, "part-1a")
    page.click("#rl-reset")
    client_id = unique("e2e-tier")
    send(page, client_id, "free", 1)
    expect(page.locator("#rl-tier-warning")).to_be_hidden()
    send(page, client_id, "premium", 2)
    warning = page.locator("#rl-tier-warning")
    expect(warning).to_be_visible()
    expect(warning).to_contain_text("free")


def test_reset_clears_history(page):
    open_section(page, "part-1a")
    page.click("#rl-reset")
    send(page, unique("e2e-reset"), "free", 1)
    page.click("#rl-reset")
    expect(page.locator("#rl-history tr.history-row")).to_have_count(0)
    expect(page.locator("#rl-notice")).to_contain_text("reset")


def test_invalid_client_id_shows_server_validation(page, expect_api_status):
    expect_api_status(422)
    open_section(page, "part-1a")
    page.click("#rl-reset")
    page.fill("#rl-client-id", "bad id!")
    page.click("#rl-send")
    outcome = page.locator("#rl-last-outcome")
    expect(outcome).to_contain_text("Invalid input")
    expect(outcome).to_contain_text("client_id")
    expect(page.locator("#rl-history tr.history-row")).to_have_count(0)


def test_server_restart_clears_stale_history(page, live_server):
    open_section(page, "part-1a")
    page.click("#rl-reset")
    send(page, unique("e2e-restart"), "free", 1)
    live_server.app.state.server_instance = f"restarted-{uuid.uuid4()}"
    page.fill("#rl-client-id", unique("e2e-after"))
    page.click("#rl-send")
    expect(page.locator("#rl-notice")).to_contain_text("restarted")
    expect(page.locator("#rl-history tr.history-row")).to_have_count(1)
