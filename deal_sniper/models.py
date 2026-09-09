from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Listing:
    title: str
    price: float
    url: str
    source: str
    query: str = ""
    extra: dict = field(default_factory=dict)
    id: str | None = None
    timestamp: datetime | float | None = None
    raw: dict | str | None = None

    def to_dict(self) -> dict:
        """Return JSON-compatible metadata, retaining unknown timestamps as None."""
        return {
            "title": self.title,
            "price": self.price,
            "url": self.url,
            "source": self.source,
            "query": self.query,
            "extra": self.extra,
            "id": self.id,
            "timestamp": (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else self.timestamp
            ),
            "raw": self.raw,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Listing:
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return cls(
            title=data["title"],
            price=float(data["price"]),
            url=data["url"],
            source=data["source"],
            query=data.get("query", ""),
            extra=data.get("extra", {}),
            id=data.get("id"),
            timestamp=timestamp,
            raw=data.get("raw"),
        )
