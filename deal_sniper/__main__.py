import argparse

from deal_sniper.config import Config
from deal_sniper.notifiers.console import ConsoleNotifier
from deal_sniper.poller import run_loop
from deal_sniper.sources.mock_html import MockHtmlSource
from deal_sniper.sources.mock_json import MockJsonSource

_SOURCES = {
    "mock_json": MockJsonSource,
    "mock_html": MockHtmlSource,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Deal Sniper — find below-median listings")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    parser.add_argument(
        "--source",
        required=True,
        choices=list(_SOURCES),
        help="Source to fetch listings from",
    )
    parser.add_argument("--fixture", required=True, help="Path to fixture/data file for the source")
    args = parser.parse_args()

    config = Config.from_file(args.config)
    source = _SOURCES[args.source](args.fixture)
    notifier = ConsoleNotifier()
    run_loop(config, source, notifier)


if __name__ == "__main__":
    main()
