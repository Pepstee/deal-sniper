from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    price_max: float
    keywords: list[str]
    percent_below_median: float
    poll_interval_s: int
    db_path: str

    @classmethod
    def from_file(cls, path: str | Path) -> Config:
        data = json.loads(Path(path).read_text())
        return cls(
            price_max=float(data["price_max"]),
            keywords=list(data["keywords"]),
            percent_below_median=float(data["percent_below_median"]),
            poll_interval_s=int(data["poll_interval_s"]),
            db_path=str(data["db_path"]),
        )
