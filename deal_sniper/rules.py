from __future__ import annotations

from deal_sniper.config import Config
from deal_sniper.models import Listing


class RulesEngine:
    def __init__(self, config: Config, tracker=None) -> None:
        self._config = config
        self._tracker = tracker

    def _get_median(self, trk, query: str) -> float | None:
        if trk is None:
            return None
        # Old MedianTracker (deal_sniper.median) has add(); new (tracker.py) has update().
        if hasattr(trk, "add"):
            return trk.median()
        return trk.median(query)

    def matches(self, listing: Listing, config: Config | None = None, tracker=None) -> bool:
        cfg = config if config is not None else self._config
        trk = tracker if tracker is not None else self._tracker

        if cfg.price_max and listing.price > cfg.price_max:
            return False

        if cfg.keywords:
            title_lower = listing.title.lower()
            if not all(kw.lower() in title_lower for kw in cfg.keywords):
                return False

        if cfg.below_median_pct:
            med = self._get_median(trk, listing.query or "")
            if med is not None:
                threshold = med * (1 - cfg.below_median_pct / 100)
                if listing.price > threshold:
                    return False

        return True
