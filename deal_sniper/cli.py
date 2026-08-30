import argparse
import json
import sys
from pathlib import Path

from deal_sniper.config import Config, default_config
from deal_sniper.loop import run_loop
from deal_sniper.notifier import ConsoleNotifier
from deal_sniper.rules import RulesEngine
from deal_sniper.store import SQLiteStore
from deal_sniper.tracker import MedianTracker


def _run_config_init(arguments: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="deal-sniper config-init",
        description="Write a default local Deal Sniper configuration",
    )
    parser.add_argument("--output", required=True, help="Destination JSON file")
    args = parser.parse_args(arguments)
    output = Path(args.output)
    output.write_text(json.dumps(default_config(), indent=2) + "\n", encoding="utf-8")
    print(f"Config written to {output}")


def main(argv: list[str] | None = None) -> None:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["config-init"]:
        _run_config_init(arguments[1:])
        return

    parser = argparse.ArgumentParser(description="Deal Sniper — find below-median listings")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    parser.add_argument("--source", required=True, help="Source name (e.g. mock_html, mock_json)")
    parser.add_argument("--fixture", help="Path to fixture file (HTML or JSON) for mock sources")
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Number of poll iterations (default: run forever)",
    )
    args = parser.parse_args(arguments)

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
