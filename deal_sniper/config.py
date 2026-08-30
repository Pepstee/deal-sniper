from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Config:
    price_max: float
    keywords: list[str]
    below_median_pct: float
    poll_interval_s: int
    db_path: str
    min_price: float | None = None
    exclude_keywords: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Config:
        min_price = data.get("min_price")
        return cls(
            price_max=float(data["price_max"]),
            keywords=list(data["keywords"]),
            below_median_pct=float(data["below_median_pct"]),
            poll_interval_s=int(data["poll_interval_s"]),
            db_path=str(data["db_path"]),
            min_price=float(min_price) if min_price is not None else None,
            exclude_keywords=list(data.get("exclude_keywords") or []),
        )
