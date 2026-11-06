"""Part 1B demonstration in Edge with Gemini faked at the SDK boundary (US2; task T030)."""

import json

import pytest
from google.genai import errors
from playwright.sync_api import expect

from tests.e2e.conftest import open_section

pytestmark = pytest.mark.e2e

MARKUP = "<img src=x onerror=alert(1)>"


def findings_output():
    return json.dumps({
        "status": "success",
        "findings": [
            {
                "vulnerability": "SQL Injection",
                "severity": "High",
                "description": f"Untrusted input reaches SQL. {MARKUP}",
                "evidence": "SELECT",
                "remediation": "Use parameterised queries.",
            },
            {
                "vulnerability": "Information Exposure",
                "severity": "Low",
                "description": "Returns full rows.",
                "evidence": "fetchall",
                "remediation": "Select only needed columns.",
            },
        ],
    })


def test_blank_input_disables_analysis(page, sentinel_key):
    open_section(page, "part-1b")
    page.fill("#rv-code", "   \n  ")
    expect(page.locator("#rv-analyze")).to_be_disabled()
    page.fill("#rv-code", "print('hello')")
    expect(page.locator("#rv-analyze")).to_be_enabled()
    expect(page.locator("#rv-count")).to_contain_text("14")


def test_findings_render_as_text_with_live_checks(page, sentinel_key, fake_gemini):
    fake_gemini(findings_output())
    dialogs = []
    page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
    open_section(page, "part-1b")
    page.click("#rv-samples button >> nth=0")
    expect(page.locator("#rv-code")).not_to_have_value("")
    page.click("#rv-analyze")

    cards = page.locator("#rv-findings .finding")
    expect(cards).to_have_count(2)
    expect(cards.nth(0)).to_contain_text("SQL Injection")
    expect(cards.nth(0)).to_contain_text("High")
    expect(cards.nth(0)).to_contain_text(MARKUP)
    expect(cards.nth(0)).to_contain_text("Use parameterised queries.")
    assert page.locator("#rv-findings img").count() == 0
    assert dialogs == []

    checks = page.locator("#rv-live-checks")
    expect(checks).to_contain_text("Layer 1")
    expect(checks).to_contain_text("Layer 2")
    expect(checks).to_contain_text("not applicable")
    expect(page.locator("#rv-status")).to_contain_text("gemini-3.5-flash-lite")
    expect(page.locator("#rv-raw pre")).to_contain_text('"status": "success"')


def test_no_findings_message_does_not_claim_security(page, sentinel_key, fake_gemini):
    fake_gemini(json.dumps({"status": "success", "findings": []}))
    open_section(page, "part-1b")
    page.fill("#rv-code", "def add(a, b):\n    return a + b")
    page.click("#rv-analyze")
    findings = page.locator("#rv-findings")
    expect(findings).to_contain_text("no findings")
    expect(findings).to_contain_text("does not prove")


def test_quota_error_is_shown_without_findings(page, sentinel_key, fake_gemini, expect_api_status):
    expect_api_status(429)
    fake_gemini(errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}}))
    open_section(page, "part-1b")
    page.fill("#rv-code", "eval(user_data)")
    page.click("#rv-analyze")
    expect(page.locator("#rv-status")).to_contain_text("quota")
    expect(page.locator("#rv-findings .finding")).to_have_count(0)


def test_missing_key_is_explained(page, no_key, expect_api_status):
    expect_api_status(503)
    open_section(page, "part-1b")
    page.fill("#rv-code", "eval(user_data)")
    page.click("#rv-analyze")
    expect(page.locator("#rv-status")).to_contain_text("not configured")
