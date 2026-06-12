from __future__ import annotations

import time

from deal_sniper.config import Config
from deal_sniper.rules import RulesEngine
from deal_sniper.store import SQLiteStore
from deal_sniper.tracker import MedianTracker


def run_loop(source, config: Config, store: SQLiteStore, tracker: MedianTracker,
             rules: RulesEngine, notifiers, iterations=None) -> None:
    _notifiers = notifiers if isinstance(notifiers, list) else [notifiers]
    count = 0
    while iterations is None or count < iterations:
        listings = source.fetch("") if hasattr(source, "fetch") else []
        for listing in listings:
            tracker.update(listing.query or "", listing.price)
            if store.is_new(listing):
                store.mark_seen(listing)
                if rules.matches(listing, config, tracker):
                    for n in _notifiers:
                        n.alert(listing)
        count += 1
        if (iterations is None or count < iterations) and config.poll_interval_s > 0:
            time.sleep(config.poll_interval_s)
