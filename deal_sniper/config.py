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

    keyword_mode: str = "all"
    median_mode: str = "sequential"
    deduplicate_observations: bool = False

    def __post_init__(self) -> None:
        if self.keyword_mode not in {"all", "any"}:
            raise ValueError("keyword_mode must be all or any")
        if self.median_mode not in {"sequential", "batch"}:
            raise ValueError("median_mode must be sequential or batch")
        if not isinstance(self.deduplicate_observations, bool):
            raise ValueError("deduplicate_observations must be boolean")

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
            keyword_mode=data.get("keyword_mode", "all"),
            median_mode=data.get("median_mode", "sequential"),
            deduplicate_observations=data.get("deduplicate_observations", False),
        )


def default_config() -> dict[str, object]:
    """Return a runnable configuration using only canonical local defaults."""

    return {
        "price_max": 300.0,
        "min_price": None,
        "keywords": [],
        "exclude_keywords": [],
        "below_median_pct": 0.0,
        "poll_interval_s": 300,
        "db_path": "deals.db",
    }
