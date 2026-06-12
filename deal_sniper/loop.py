from __future__ import annotations

from deal_sniper.config import Config
from deal_sniper.notifier import Notifier
from deal_sniper.rules import RulesEngine
from deal_sniper.store import SQLiteStore
from deal_sniper.tracker import MedianTracker


def run_loop(source, config: Config, store: SQLiteStore, tracker: MedianTracker,
             engine: RulesEngine, notifier: Notifier) -> None:
    listings = source.fetch("") if hasattr(source, "fetch") else []
    for listing in listings:
        tracker.update(listing.query or "", listing.price)
        if store.is_new(listing):
            store.mark_seen(listing)
            if engine.matches(listing, config, tracker):
                notifier.alert(listing)
