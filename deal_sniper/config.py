from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Config:
    price_max: float
    keywords: list[str]
    below_median_pct: float
    poll_interval_s: int
    db_path: str

    @classmethod
    def from_dict(cls, data: dict) -> Config:
        return cls(
            price_max=float(data["price_max"]),
            keywords=list(data["keywords"]),
            below_median_pct=float(data["below_median_pct"]),
            poll_interval_s=int(data["poll_interval_s"]),
            db_path=str(data["db_path"]),
        )
