from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Config:
    price_max: float
    keywords: list[str]
    percent_below: float
    poll_interval: int
    db_path: str

    @classmethod
    def from_dict(cls, data: dict) -> Config:
        return cls(
            price_max=float(data["price_max"]),
            keywords=list(data["keywords"]),
            percent_below=float(data["percent_below"]),
            poll_interval=int(data["poll_interval"]),
            db_path=str(data["db_path"]),
        )
