#!/usr/bin/env python3
"""Acceptance demo: pipeline on fixture files, stdlib only, no network I/O."""
from __future__ import annotations

import pathlib

from deal_sniper.config import Config
from deal_sniper.loop import run_loop
from deal_sniper.notifier import ConsoleNotifier
from deal_sniper.rules import RulesEngine
from deal_sniper.sources.mock_html import MockHtmlSource
from deal_sniper.sources.mock_json import MockJsonSource
from deal_sniper.store import SQLiteStore
from deal_sniper.tracker import MedianTracker

ROOT = pathlib.Path(__file__).parent
HTML_FIXTURE = ROOT / "tests" / "fixtures" / "sample.html"
JSON_FIXTURE = ROOT / "tests" / "fixtures" / "sample.json"


class _CountingNotifier(ConsoleNotifier):
    def __init__(self) -> None:
        self.count = 0

    def alert(self, listing) -> None:
        self.count += 1
        super().alert(listing)


def main() -> None:
    config = Config(
        price_max=200.0,
        keywords=[],
        below_median_pct=0.0,
        poll_interval_s=0,
        db_path=":memory:",
    )
    store = SQLiteStore(":memory:")
    tracker = MedianTracker()
    engine = RulesEngine(config, tracker)
    notifier = _CountingNotifier()

    print("--- Poll 1: HTML fixture ---")
    run_loop(MockHtmlSource(HTML_FIXTURE), config, store, tracker, engine, notifier)

    print("--- Poll 2: JSON fixture (dedup applies) ---")
    run_loop(MockJsonSource(JSON_FIXTURE), config, store, tracker, engine, notifier)

    print(f"\nFinished 2 poll cycles — {notifier.count} deal alert(s) surfaced.")
    if notifier.count == 0:
        raise SystemExit("acceptance FAILED: no alerts produced")


if __name__ == "__main__":
    main()
