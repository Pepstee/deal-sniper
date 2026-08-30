#!/usr/bin/env python3
"""Acceptance demo: pipeline on fixture data, stdlib only, no network I/O."""

from __future__ import annotations

import pathlib

from deal_sniper.config import Config
from deal_sniper.loop import run_loop
from deal_sniper.notifier import ConsoleNotifier
from deal_sniper.rules import RulesEngine
from deal_sniper.sources.mock_json import MockJsonSource as FixtureSource
from deal_sniper.store import SQLiteStore
from deal_sniper.tracker import MedianTracker

ROOT = pathlib.Path(__file__).parent
FIXTURE = ROOT / "fixtures" / "sample.json"


class _CountingNotifier(ConsoleNotifier):
    def __init__(self) -> None:
        self.count = 0

    def alert(self, listing) -> None:
        self.count += 1
        super().alert(listing)


def main() -> None:
    config = Config(
        price_max=300.0,
        min_price=50.0,
        keywords=[],
        exclude_keywords=["sofa"],
        below_median_pct=0.0,
        poll_interval_s=0,
        db_path=":memory:",
    )
    store = SQLiteStore(":memory:")
    tracker = MedianTracker()
    rules = RulesEngine(config, tracker)
    notifier = _CountingNotifier()

    source = FixtureSource(FIXTURE)
    run_loop(source, config, store, tracker, rules, notifier, iterations=1)

    if notifier.count != 1:
        raise SystemExit(f"acceptance FAILED: expected 1 ALERT, got {notifier.count}")
    print(f"acceptance OK — {notifier.count} ALERT(s) produced")


if __name__ == "__main__":
    main()
