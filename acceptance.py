#!/usr/bin/env python3
"""Acceptance demo: two poll cycles using fixture files, stdlib only, no live URLs."""
from __future__ import annotations

import json
import pathlib
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).parent
HTML_FIXTURE = ROOT / "fixtures" / "sample.html"
JSON_FIXTURE = ROOT / "fixtures" / "sample.json"

PRICE_MAX = 200.0  # filters out the $299.50 Trek bike


class _ListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._listings: list[dict] = []
        self._current: dict | None = None
        self._capture = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attr = dict(attrs)
        if tag == "li" and attr.get("class") == "listing":
            self._current = {
                "url": attr.get("data-url", ""),
                "price": float(attr.get("data-price", 0)),
            }
        elif tag == "span" and attr.get("class") == "title" and self._current is not None:
            self._capture = True

    def handle_data(self, data: str) -> None:
        if self._capture and self._current is not None:
            self._current["title"] = data.strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "span":
            self._capture = False
        elif tag == "li" and self._current is not None:
            self._listings.append(dict(self._current))
            self._current = None


def _fetch_html() -> list[dict]:
    parser = _ListingParser()
    parser.feed(HTML_FIXTURE.read_text())
    return parser._listings


def _fetch_json() -> list[dict]:
    return json.loads(JSON_FIXTURE.read_text())


def _matches(item: dict) -> bool:
    return item["price"] <= PRICE_MAX


def _poll_cycle(num: int, items: list[dict], seen: set) -> int:
    print(f"\n--- Poll cycle {num} (source: {'html' if num == 1 else 'json'}) ---")
    alerts = 0
    for item in items:
        key = item["url"]
        if key not in seen:
            seen.add(key)
            if _matches(item):
                print(f"DEAL ALERT: {item['title']} | ${item['price']:.2f} | {item['url']}")
                alerts += 1
    if alerts == 0:
        print("(no new deals this cycle)")
    return alerts


def main() -> None:
    seen: set = set()
    total = _poll_cycle(1, _fetch_html(), seen)
    total += _poll_cycle(2, _fetch_json(), seen)

    print(f"\nFinished 2 poll cycles — {total} deal alert(s) surfaced.")
    if total == 0:
        raise SystemExit("acceptance FAILED: no alerts produced")


if __name__ == "__main__":
    main()
