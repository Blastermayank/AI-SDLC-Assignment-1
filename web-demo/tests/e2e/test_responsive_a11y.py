"""Responsive layout, keyboard use, visible focus, first render and contrast.

SC-009 and constitution constraints (WCAG AA contrast, first render under 1 s); task T053.
"""

import re

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import open_section

pytestmark = pytest.mark.e2e

ROUTES = ["overview", "methodology", "part-1a", "part-1b", "evaluation", "evidence"]

COLOR_PAIR_JS = """
(selector) => {
  const node = document.querySelector(selector);
  const parse = (c) => (c.match(/[\\d.]+/g) || []).map(Number);
  let bgNode = node;
  let bg = getComputedStyle(bgNode).backgroundColor;
  const clear = (c) => c === 'transparent' || (parse(c).length === 4 && parse(c)[3] === 0);
  while (bgNode && clear(bg)) {
    bgNode = bgNode.parentElement;
    bg = getComputedStyle(bgNode || document.body).backgroundColor;
  }
  return { fg: parse(getComputedStyle(node).color), bg: parse(bg) };
}
"""

SAMPLES = {
    "body": "p",
    "muted": ".muted",
    "link": "a.sample-link",
    "primary button": ".btn-primary",
    "secondary button": ".btn-secondary",
    "pass badge": ".badge-pass",
    "fail badge": ".badge-fail",
    "warn badge": ".badge-warn",
    "info badge": ".badge-info",
    "neutral badge": ".badge-neutral",
    "callout": ".callout",
}


def luminance(rgb):
    def channel(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    light, dark = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


@pytest.mark.parametrize("route", ROUTES)
def test_no_horizontal_scroll_at_360px(page, route):
    page.set_viewport_size({"width": 360, "height": 780})
    open_section(page, route)
    page.wait_for_timeout(300)
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 0, f"{route} overflows by {overflow}px"


def test_mobile_menu_opens_and_closes(page):
    page.set_viewport_size({"width": 360, "height": 780})
    page.goto("/")
    toggle = page.locator("#nav-toggle")
    expect(toggle).to_be_visible()
    toggle.click()
    expect(page.locator("#sidebar")).to_have_class(re.compile("is-open"))
    page.click(".nav-list a[data-route='evidence']")
    expect(page.locator("#section-evidence")).to_be_visible()
    expect(page.locator("#sidebar")).not_to_have_class(re.compile("is-open"))


def test_desktop_hides_menu_button(page):
    page.goto("/")
    expect(page.locator("#nav-toggle")).to_be_hidden()


def test_part1a_controls_are_keyboard_operable_with_visible_focus(page):
    open_section(page, "part-1a")
    page.click("#rl-reset")
    page.focus("#h-part-1a")
    reached = set()
    for _ in range(40):
        page.keyboard.press("Tab")
        focused = page.evaluate("document.activeElement.id")
        if focused in {"rl-client-id", "rl-tier", "rl-send", "rl-reset"}:
            reached.add(focused)
            outline = page.evaluate(
                "(() => { const s = getComputedStyle(document.activeElement);"
                " return [s.outlineStyle, parseFloat(s.outlineWidth)]; })()"
            )
            assert outline[0] != "none", f"no focus outline on {focused}"
            assert outline[1] >= 2, f"focus outline thinner than 2px on {focused}"
        if len(reached) == 4:
            break
    assert reached == {"rl-client-id", "rl-tier", "rl-send", "rl-reset"}

    page.fill("#rl-client-id", "keyboard-client")
    page.focus("#rl-send")
    page.keyboard.press("Enter")
    expect(page.locator("#rl-history tr.history-row")).to_have_count(1)


def test_space_activates_sample_button(page):
    open_section(page, "part-1b")
    page.focus("#rv-samples button >> nth=0")
    page.keyboard.press("Space")
    expect(page.locator("#rv-code")).not_to_have_value("")


def test_first_render_under_one_second(page):
    page.goto("/")
    elapsed = page.evaluate(
        "performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd"
    )
    assert elapsed < 1000, f"DOMContentLoaded at {elapsed:.0f} ms"


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_contrast_meets_wcag_aa(page, theme):
    page.goto("/")
    page.evaluate(
        """(theme) => {
          document.documentElement.dataset.theme = theme;
          const holder = document.createElement('div');
          holder.className = 'card';
          for (const kind of ['pass', 'fail', 'warn', 'info', 'neutral']) {
            const span = document.createElement('span');
            span.className = `badge badge-${kind}`;
            span.textContent = kind;
            holder.append(span);
          }
          const link = document.createElement('a');
          link.className = 'sample-link';
          link.href = '#overview';
          link.textContent = 'link';
          holder.append(link);
          document.getElementById('section-overview').append(holder);
        }""",
        theme,
    )
    failures = []
    for name, selector in SAMPLES.items():
        pair = page.evaluate(COLOR_PAIR_JS, selector)
        ratio = contrast(pair["fg"], pair["bg"])
        if ratio < 4.5:
            failures.append(f"{name}: {ratio:.2f}")
    assert not failures, f"{theme} theme below 4.5:1 -> {failures}"
