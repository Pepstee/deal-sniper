from __future__ import annotations

from deal_sniper.config import Config
from deal_sniper.listing import Listing


class RulesEngine:
    def __init__(self, config: Config) -> None:
        self._config = config

    def matches(self, listing: Listing, median: float | None) -> bool:
        cfg = self._config

        if cfg.price_max and listing.price > cfg.price_max:
            return False

        if cfg.keywords:
            title_lower = listing.title.lower()
            if not all(kw.lower() in title_lower for kw in cfg.keywords):
                return False

        if cfg.percent_below and median is not None:
            threshold = median * (1 - cfg.percent_below / 100)
            if listing.price > threshold:
                return False

        return True
