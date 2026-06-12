import argparse
import json
from pathlib import Path

from deal_sniper.config import Config
from deal_sniper.loop import run_loop
from deal_sniper.notifier import ConsoleNotifier
from deal_sniper.rules import RulesEngine
from deal_sniper.store import SQLiteStore
from deal_sniper.tracker import MedianTracker


def main() -> None:
    parser = argparse.ArgumentParser(description="Deal Sniper — find below-median listings")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    parser.add_argument("--source", required=True, help="Source name (e.g. mock_html, mock_json)")
    parser.add_argument("--fixture", help="Path to fixture file (HTML or JSON) for mock sources")
    parser.add_argument("--iterations", type=int, default=None,
                        help="Number of poll iterations (default: run forever)")
    args = parser.parse_args()

    cfg_data = json.loads(Path(args.config).read_text())
    config = Config.from_dict(cfg_data)
    store = SQLiteStore(config.db_path)
    tracker = MedianTracker()
    rules = RulesEngine(config, tracker)
    notifier = ConsoleNotifier()

    if args.fixture:
        fixture_path = Path(args.fixture)
        if args.source == "mock_html" or fixture_path.suffix == ".html":
            from deal_sniper.sources.mock_html import MockHtmlSource
            source = MockHtmlSource(fixture_path)
        else:
            from deal_sniper.sources.mock_json import MockJsonSource
            source = MockJsonSource(fixture_path)
    else:
        raise SystemExit(f"No source implementation for '{args.source}' without --fixture")

    run_loop(source, config, store, tracker, rules, notifier, iterations=args.iterations)
    store.close()


if __name__ == "__main__":
    main()
