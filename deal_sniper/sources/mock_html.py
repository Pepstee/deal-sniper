from html.parser import HTMLParser
from pathlib import Path

from deal_sniper.models import Listing
from deal_sniper.source import Source


class _ListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._listings: list[Listing] = []
        self._current: dict | None = None
        self._capture_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "li" and attr.get("class") == "listing":
            self._current = {"url": attr.get("data-url", ""), "price": float(attr.get("data-price", 0))}
        elif tag == "span" and attr.get("class") == "title" and self._current is not None:
            self._capture_title = True

    def handle_data(self, data: str) -> None:
        if self._capture_title and self._current is not None:
            self._current["title"] = data.strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "span":
            self._capture_title = False
        elif tag == "li" and self._current is not None:
            self._listings.append(
                Listing(
                    title=self._current.get("title", ""),
                    price=self._current["price"],
                    url=self._current["url"],
                    source="mock_html",
                )
            )
            self._current = None


class MockHtmlSource(Source):
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def fetch(self, query: str) -> list[Listing]:
        parser = _ListingParser()
        parser.feed(self._path.read_text())
        return parser._listings
