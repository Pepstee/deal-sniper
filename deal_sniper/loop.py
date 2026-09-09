from __future__ import annotations

import time
from dataclasses import replace

from deal_sniper.config import Config
from deal_sniper.rules import RulesEngine
from deal_sniper.store import SQLiteStore
from deal_sniper.tracker import MedianTracker


def run_loop(source, config: Config, store: SQLiteStore, tracker: MedianTracker,
             rules: RulesEngine, notifiers, iterations=None, *, query: str = "") -> int:
    """Poll a source and return the number of newly alerted listings.

    Existing sequential/repeated-observation semantics remain defaults. Batch
    mode records the whole poll before filtering; deduplication optionally
    records only unseen URLs, including duplicate rows within the same poll.
    """
    _notifiers = notifiers if isinstance(notifiers, list) else [notifiers]
    count = 0
    alerts = 0
    while iterations is None or count < iterations:
        listings = source.fetch(query)
        if query:
            listings = [replace(listing, query=query) for listing in listings]
        observed: set[str] = set()

        def record(listing):
            if config.deduplicate_observations:
                if listing.url in observed or not (store.is_new(listing, query=query) if query else store.is_new(listing)):
                    return
                observed.add(listing.url)
            tracker.update(listing.query or "", listing.price)

        if config.median_mode == "batch":
            for listing in listings:
                record(listing)
        for listing in listings:
            if config.median_mode == "sequential":
                record(listing)
            if (store.is_new(listing, query=query) if query else store.is_new(listing)):
                if query:
                    store.mark_seen(listing, query=query)
                else:
                    store.mark_seen(listing)
                if rules.matches(listing, config, tracker):
                    for notifier in _notifiers:
                        notifier.alert(listing)
                    alerts += 1
        count += 1
        if (iterations is None or count < iterations) and config.poll_interval_s > 0:
            time.sleep(config.poll_interval_s)
    return alerts
