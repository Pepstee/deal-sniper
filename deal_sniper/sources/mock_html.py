from html.parser import HTMLParser
from pathlib import Path

from deal_sniper.models import Listing
from deal_sniper.source import Source
from deal_sniper.sources.mock_json import parse_price


class _ListingParser(HTMLParser):
    """Read the canonical li format and archived div/table listing formats."""

    def __init__(self, query: str = "", source: str = "mock_html") -> None:
        super().__init__()
        self._listings: list[Listing] = []
        self._current = None
        self._stack = []
        self._capture = None
        self._capture_depth = 0
        self._query = query
        self._source = source

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        classes = (attr.get("class") or "").split()
        if tag in {"li", "div", "tr"} and "listing" in classes:
            self._current = {
                "url": attr.get("data-url") or "", "price": attr.get("data-price", "0"),
                "title": "", "source": attr.get("data-source") or self._source,
                "id": attr.get("data-id") or "",
            }
            self._stack = [tag]
            self._capture = None
            return
        if self._current is None:
            return
        if tag not in {"br", "img", "input", "hr", "meta", "link", "wbr", "source", "area", "embed", "param", "track", "col", "base"}:
            self._stack.append(tag)
        for field in ("title", "price", "source", "url"):
            if field in classes or f"listing-{field}" in classes:
                self._capture = field
                self._capture_depth = len(self._stack)
                self._current[field] = ""
                break
        if tag == "a" and attr.get("href"):
            self._current["url"] = attr["href"]
            if self._capture == "url":
                self._capture = None

    def handle_data(self, data):
        if self._current is not None and self._capture:
            self._current[self._capture] += data

    def handle_endtag(self, tag):
        if self._current is None or tag not in self._stack:
            return
        idx = len(self._stack) - 1 - self._stack[::-1].index(tag)
        self._stack = self._stack[:idx]
        if self._capture and len(self._stack) < self._capture_depth:
            self._capture = None
        if self._stack:
            return
        item = self._current
        self._current = None
        try:
            if not item["url"].strip():
                return
            self._listings.append(Listing(
                title=item["title"].strip(), price=parse_price(item["price"]),
                url=item["url"].strip(), source=item["source"].strip() or self._source,
                query=self._query, extra=dict(item), id=item["id"] or None,
            ))
        except (TypeError, ValueError):
            pass


def parse_html(raw: str, query: str = "", source: str = "mock_html") -> list[Listing]:
    parser = _ListingParser(query, source)
    parser.feed(raw)
    parser.close()
    return parser._listings


class MockHtmlSource(Source):
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def fetch(self, query: str) -> list[Listing]:
        return parse_html(self._path.read_text(encoding="utf-8"), query)
