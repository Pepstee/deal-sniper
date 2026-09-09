import argparse
import json
import sys
import time
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


def _run_list_seen(arguments: list[str], *, full: bool = False) -> None:
    parser = argparse.ArgumentParser(
        prog="deal-sniper list-seen",
        description="Print persisted seen listing URLs",
    )
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    args = parser.parse_args(arguments)

    try:
        cfg_data = json.loads(Path(args.config).read_text(encoding="utf-8"))
        config = Config.from_dict({**default_config(), **cfg_data})
    except (OSError, TypeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    store = SQLiteStore(config.db_path)
    try:
        if full:
            print(json.dumps([listing.to_dict() for listing in store.get_all()], indent=2))
        else:
            for url in store.list_seen_urls():
                print(url)
    finally:
        store.close()


def _make_source(name: str, fixture: str | None = None, url: str | None = None, format: str = "json"):
    if name == "http":
        from deal_sniper.source import HttpSource
        if not url:
            raise ValueError("http source requires a URL")
        return HttpSource(url, format=format)
    if not fixture:
        raise ValueError(f"source '{name}' requires a local fixture")
    if name not in {"mock_html", "mock_json", "local"}:
        raise ValueError(f"unknown source '{name}'")
    if name == "mock_html" or (name == "local" and Path(fixture).suffix.lower() in {".html", ".htm"}):
        from deal_sniper.sources.mock_html import MockHtmlSource
        return MockHtmlSource(fixture)
    from deal_sniper.sources.mock_json import MockJsonSource
    return MockJsonSource(fixture)


def _run_queries(data: dict, iterations: int | None) -> int:
    """Run all configured queries fairly, with each query's own polling interval."""
    raw_queries = data["queries"]
    if not isinstance(raw_queries, list) or not raw_queries:
        raise ValueError("queries must be a non-empty list")
    contexts = []
    names = set()
    for raw in raw_queries:
        name = raw["name"]
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("query names must be non-empty and unique")
        names.add(name)
        values = default_config()
        values.update({k: v for k, v in data.items() if k in Config.__dataclass_fields__})
        query_rules = dict(raw.get("rules", {}))
        if "max_percent_below_median" in query_rules:
            raise ValueError("legacy max_percent_below_median had inverted semantics; use below_median_pct explicitly")
        aliases = {"max_price": "price_max", "include_keywords": "keywords"}
        values.update({aliases.get(k, k): v for k, v in query_rules.items()})
        values["poll_interval_s"] = raw.get("poll_interval_sec", raw.get("poll_interval_s", values["poll_interval_s"]))
        cfg = Config.from_dict(values)
        if cfg.poll_interval_s < 0:
            raise ValueError("query poll interval must be nonnegative")
        source = _make_source(raw.get("source", raw.get("source_type", "local")),
                              raw.get("fixture", raw.get("source_path")), raw.get("url"), raw.get("format", "json"))
        contexts.append({"source": source, "config": cfg, "query": name,
                         "search_term": raw.get("search_term", raw.get("query", name)),
                         "next": 0.0, "completed": 0})
    store = SQLiteStore(str(data.get("db_path", "deals.db")))
    tracker = MedianTracker()
    notifier = ConsoleNotifier()
    alerts = 0
    try:
        while True:
            pending = [c for c in contexts if iterations is None or c["completed"] < iterations]
            if not pending:
                return alerts
            now = time.monotonic()
            wait = min(c["next"] for c in pending) - now
            if wait > 0:
                time.sleep(wait)
                continue
            for context in pending:
                if context["next"] > time.monotonic():
                    continue
                cfg = context["config"]
                # Source search and median grouping are separate identities.
                source = context["source"]
                search = context["search_term"]
                class QuerySource:
                    def fetch(self, query):
                        return source.fetch(search)
                alerts += run_loop(QuerySource(), cfg, store, tracker, RulesEngine(cfg, tracker),
                                   notifier, iterations=1, query=context["query"])
                context["completed"] += 1
                context["next"] = time.monotonic() + cfg.poll_interval_s
    finally:
        store.close()


def main(argv: list[str] | None = None) -> None:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["config-init"]:
        _run_config_init(arguments[1:])
        return
    if arguments[:1] in (["list-seen"], ["list-listings"]):
        _run_list_seen(arguments[1:], full=arguments[0] == "list-listings")
        return

    parser = argparse.ArgumentParser(description="Deal Sniper — find below-median listings")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    parser.add_argument("--source", help="Source name (e.g. mock_html, mock_json)")
    parser.add_argument("--fixture", help="Path to fixture file (HTML or JSON) for mock sources")
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Number of poll iterations (default: run forever)",
    )
    parser.add_argument("--url", help="Explicit HTTP source URL")
    parser.add_argument("--format", choices=["json", "html"], default="json")
    args = parser.parse_args(arguments)
    if args.iterations is not None and args.iterations < 0:
        parser.error("iterations must be nonnegative")

    cfg_data = json.loads(Path(args.config).read_text())
    if "queries" in cfg_data:
        try:
            _run_queries(cfg_data, args.iterations)
        except KeyboardInterrupt:
            print("Polling interrupted.", file=sys.stderr)
        return
    if not args.source:
        parser.error("--source is required for a single-query configuration")
    config = Config.from_dict(cfg_data)
    store = SQLiteStore(config.db_path)
    tracker = MedianTracker()
    rules = RulesEngine(config, tracker)
    notifier = ConsoleNotifier()

    try:
        source = _make_source(args.source, args.fixture, args.url, args.format)
        run_loop(source, config, store, tracker, rules, notifier, iterations=args.iterations)
    except KeyboardInterrupt:
        print("Polling interrupted.", file=sys.stderr)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    finally:
        store.close()


if __name__ == "__main__":
    main()
