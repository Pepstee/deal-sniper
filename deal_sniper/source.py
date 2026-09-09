from abc import ABC, abstractmethod

from deal_sniper.models import Listing


class Source(ABC):
    """A listing source: return the current listings for a query."""

    @abstractmethod
    def fetch(self, query: str) -> list[Listing]: ...


class HttpSource(Source):
    """Fetch an explicitly supplied HTTP URL and reuse the local listing parsers."""

    def __init__(self, url: str, format: str = "json", timeout: float = 10.0) -> None:
        import math
        from urllib.parse import urlsplit

        if urlsplit(url).scheme not in {"http", "https"}:
            raise ValueError("HTTP source requires an http or https URL")
        if format not in {"json", "html"}:
            raise ValueError("HTTP format must be json or html")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("HTTP timeout must be finite and positive")
        self.url, self.format, self.timeout = url, format, timeout

    def fetch(self, query: str) -> list[Listing]:
        from urllib.request import urlopen
        from deal_sniper.sources.mock_html import parse_html
        from deal_sniper.sources.mock_json import parse_json

        with urlopen(self.url, timeout=self.timeout) as response:
            raw = response.read().decode(response.headers.get_content_charset() or "utf-8")
        parser = parse_html if self.format == "html" else parse_json
        return parser(raw, query, source="http")


def build_craigslist_url(keyword: str, category: str = "sss", max_price: float = 0) -> str:
    """Build a search URL only. This helper does not fetch marketplace content."""
    import math
    from urllib.parse import urlencode, quote

    if not math.isfinite(max_price) or max_price < 0:
        raise ValueError("Maximum price must be finite and non-negative")
    params = {"query": keyword}
    if max_price:
        params["max_ask"] = str(int(max_price))
    return "https://www.craigslist.org/search/" + quote(category or "sss", safe="") + "?" + urlencode(params)
