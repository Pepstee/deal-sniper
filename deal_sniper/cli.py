import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Deal Sniper — find below-median listings")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    parser.add_argument(
        "--source",
        required=True,
        help="Source name to query (e.g. craigslist, facebook)",
    )
    args = parser.parse_args()
    print(f"deal-sniper: config={args.config}, source={args.source} (stub)")


if __name__ == "__main__":
    main()
