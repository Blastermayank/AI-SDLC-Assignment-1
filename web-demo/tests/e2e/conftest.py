"""Browser test harness: live portal server plus Playwright driving Microsoft Edge (task T010).

Console policy (research R16): a test fails on any page error and on any console error,
except Chromium's "Failed to load resource" message for an /api/* response whose status the
test declared as expected with `expect_api_status(...)`. Expected 4xx/5xx responses are
outcomes the portal must display, not page errors.
"""

from __future__ import annotations

import re
import socket
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest
import uvicorn
from playwright.sync_api import sync_playwright

from app.config import Settings
from app.main import create_app
from tests.conftest import REPO_ROOT

RESOURCE_ERROR = re.compile(
    r"^Failed to load resource: the server responded with a status of (\d{3})"
)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def live_server():
    app = create_app(Settings.from_environment(repo_root=REPO_ROOT))
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("Live portal server did not start within 15 seconds.")
        time.sleep(0.05)
    yield SimpleNamespace(url=f"http://127.0.0.1:{port}", app=app)
    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as playwright:
        edge = playwright.chromium.launch(channel="msedge", headless=True)
        yield edge
        edge.close()


@pytest.fixture
def page_errors():
    return SimpleNamespace(errors=[], expected=set())


@pytest.fixture
def expect_api_status(page_errors):
    def register(*codes: int) -> None:
        page_errors.expected.update(codes)

    return register


@pytest.fixture
def page(browser, live_server, page_errors):
    context = browser.new_context(
        viewport={"width": 1280, "height": 900}, base_url=live_server.url
    )
    new_page = context.new_page()

    def on_console(message):
        if message.type != "error":
            return
        match = RESOURCE_ERROR.match(message.text)
        url_path = urlparse(message.location.get("url", "")).path
        if match and url_path.startswith("/api/") and int(match.group(1)) in page_errors.expected:
            return
        page_errors.errors.append(f"console: {message.text} ({message.location.get('url')})")

    new_page.on("console", on_console)
    new_page.on("pageerror", lambda error: page_errors.errors.append(f"pageerror: {error}"))
    yield new_page
    context.close()
    if page_errors.errors:
        pytest.fail("Browser reported errors:\n" + "\n".join(page_errors.errors))


def open_section(page, route: str) -> None:
    """Navigate to a portal section and wait until its view is visible."""
    page.goto(f"/#{route}")
    page.wait_for_selector(f"#section-{route}:not([hidden])")
