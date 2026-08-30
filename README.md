# deal-sniper

Polls classified listing sources and alerts you when a listing's price is meaningfully below the
median for its category — a "deal sniper" for secondhand marketplaces.

The core engine is source-agnostic: plug in any marketplace by implementing the `Source` protocol,
configure your thresholds in a JSON file, and wire up a notifier.

---

## Quickstart (acceptance demo)

No dependencies beyond the standard library are required for the demo:

```
python acceptance.py
```

This runs one simulated poll cycle against the bundled fixture file (`fixtures/sample.json`) and
prints any listings that fall below the configured price ceiling.  A non-zero exit code means the
demo failed.

---

## Live marketplace access — official APIs only

> **No scraping.** Accessing live marketplace data by scraping HTML violates the Terms of Service
> of virtually every classified-ads platform (Craigslist, Facebook Marketplace, eBay, Gumtree,
> etc.) and may expose you to legal risk.
>
> To point deal-sniper at a real site, you **must** obtain official API credentials from the
> platform and comply with all rate-limit, attribution, and data-use requirements in their
> developer programme.  The bundled `MockHtmlSource` and `MockJsonSource` are local stubs that
> use no live URLs and are suitable only for testing.

---

## Installing and running the CLI

```
pip install -e .
deal-sniper --config config.json --source mock_json --fixture fixtures/sample.json --iterations 1
```

Or without installing, from the project root:

```
python -m deal_sniper --config config.json --source mock_json --fixture fixtures/sample.json --iterations 1
```

`--source` must match a registered `Source` implementation (see below); the bundled mock sources
require `--fixture` pointing at a local data file.  Omit `--iterations` to poll forever at
`poll_interval_s`.

---

## Configuration (`config.json`)

| Key | Type | Description |
|---|---|---|
| `price_max` | float | Hard ceiling — listings above this price are ignored |
| `min_price` | float, optional | Inclusive floor — listings below this price are ignored |
| `keywords` | list[str] | All keywords must appear in a listing's title (case-insensitive) for it to alert |
| `exclude_keywords` | list[str], optional | A listing is ignored when any keyword appears in its title (case-insensitive) |
| `below_median_pct` | float | Minimum % discount vs. the rolling median to trigger an alert (e.g. `15` = 15 % below) |
| `poll_interval_s` | int | Seconds between poll cycles |
| `db_path` | str | Path to the SQLite file used to track seen listings |

Example:

```json
{
  "price_max": 300.0,
  "min_price": 50.0,
  "keywords": ["road bike"],
  "exclude_keywords": ["broken", "parts only"],
  "below_median_pct": 15,
  "poll_interval_s": 300,
  "db_path": "state/seen.db"
}
```

---

## Adding a real marketplace source

> **Important — ToS and API compliance:** scraping or accessing marketplace data without
> authorisation likely violates the platform's Terms of Service.  Before pointing deal-sniper at
> any live marketplace, obtain official API access and comply with all applicable rate-limit,
> attribution, and data-use requirements.  The bundled sources (`MockHtmlSource`,
> `MockJsonSource`) exist solely for local testing and use no live URLs.

Subclass the `Source` ABC defined in `deal_sniper/source.py`:

```python
from deal_sniper.models import Listing
from deal_sniper.source import Source

class MyMarketplaceSource(Source):
    def fetch(self, query: str) -> list[Listing]:
        # Call the official API, parse the response, return Listing objects.
        results = my_api_client.search(query)
        return [
            Listing(
                title=r["title"],
                price=float(r["price"]),
                url=r["listing_url"],
                source="my-marketplace",
            )
            for r in results
        ]
```

`Listing` fields:

| Field | Type | Notes |
|---|---|---|
| `title` | str | Human-readable listing title |
| `price` | float | Asking price in your local currency |
| `url` | str | Canonical URL for the listing |
| `source` | str | Short identifier for the marketplace |
| `extra` | dict | Optional; any additional metadata |

Register your source and pass its name to `--source` when invoking the CLI.

---

## Adding a custom notifier

Subclass the `Notifier` ABC defined in `deal_sniper/notifier.py`:

```python
from deal_sniper.models import Listing
from deal_sniper.notifier import Notifier

class SlackNotifier(Notifier):
    def __init__(self, webhook_url: str) -> None:
        self._webhook = webhook_url

    def alert(self, listing: Listing) -> None:
        import urllib.request, json
        text = f"DEAL ALERT: {listing.title} | ${listing.price:.2f} | {listing.url}"
        body = json.dumps({"text": text}).encode()
        req = urllib.request.Request(self._webhook, data=body,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req)
```

The built-in `ConsoleNotifier` (prints to stdout) is used by default.  Swap it out by passing your
notifier instance (or a list of notifiers) to `run_loop`.
