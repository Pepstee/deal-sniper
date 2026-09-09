import json
import math
from datetime import datetime
from pathlib import Path

from deal_sniper.models import Listing
from deal_sniper.source import Source


def parse_price(value) -> float:
    """Parse ordinary dollar prices and reject invalid numeric values."""
    if isinstance(value, bool):
        raise ValueError("Boolean price")
    price = float(str(value).strip().lstrip("$").replace(",", "").strip())
    if not math.isfinite(price) or price < 0:
        raise ValueError("Price must be finite and non-negative")
    return price


def parse_json(raw: str, query: str = "", source: str = "mock_json") -> list[Listing]:
    """Parse one object or an array, retaining valid rows among malformed rows."""
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("Listings JSON must be an object or array")
    listings = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            if not isinstance(item["title"], str) or not isinstance(item["url"], str):
                continue
            if not item["url"].strip():
                continue
            timestamp = item.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            elif timestamp is not None:
                if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp):
                    continue
            identifier = item.get("id")
            if identifier is not None:
                if not isinstance(identifier, (str, int)) or isinstance(identifier, bool):
                    continue
                identifier = str(identifier)
            raw_payload = item.get("raw", dict(item))
            if raw_payload is not None and not isinstance(raw_payload, (dict, str)):
                continue
            listings.append(Listing(
                title=item["title"], price=parse_price(item["price"]), url=item["url"],
                source=str(item.get("source") or source), query=query,
                extra=dict(item), id=identifier, timestamp=timestamp, raw=raw_payload,
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return listings


class MockJsonSource(Source):
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def fetch(self, query: str) -> list[Listing]:
        return parse_json(self._path.read_text(encoding="utf-8"), query)
