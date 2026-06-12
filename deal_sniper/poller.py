from __future__ import annotations

import time

from deal_sniper.config import Config
from deal_sniper.median import MedianTracker
from deal_sniper.notifier import Notifier
from deal_sniper.rules import RulesEngine
from deal_sniper.store import SQLiteStore


def poll_once(
    source,
    store: SQLiteStore,
    engine: RulesEngine,
    tracker: MedianTracker,
    notifier: Notifier,
) -> None:
    for listing in source.fetch(""):
        tracker.add(listing.price)
        if store.is_new(listing):
            store.mark_seen(listing)
            if engine.matches(listing):
                alert = f"DEAL: {listing.title} — ${listing.price:.2f}  {listing.url}"
                notifier.notify(listing, alert)


def run_loop(config: Config, source, notifier: Notifier) -> None:
    store = SQLiteStore(config.db_path)
    tracker = MedianTracker()
    engine = RulesEngine(config, tracker)
    try:
        while True:
            poll_once(source, store, engine, tracker, notifier)
            time.sleep(config.poll_interval_s)
    finally:
        store.close()
