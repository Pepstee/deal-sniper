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

This runs two simulated poll cycles against the bundled fixture files (`fixtures/sample.html` and
`fixtures/sample.json`) and prints any listings that fall below the configured price ceiling.  A
non-zero exit code means the demo failed.

---

## Installing and running the CLI

```
pip install -e .
deal-sniper --config config.json --source <source-name>
```

`<source-name>` must match a registered `Source` implementation (see below).

---

## Configuration (`config.json`)

| Key | Type | Description |
|---|---|---|
| `price_max` | float | Hard ceiling — listings above this price are ignored |
| `keywords` | list[str] | Search terms passed to each source's `fetch()` call |
| `percent_below_median` | float | Minimum % discount vs. the rolling median to trigger an alert (e.g. `15` = 15 % below) |
| `poll_interval_s` | int | Seconds between poll cycles |
| `db_path` | str | Path to the SQLite file used to track seen listings |

Example:

```json
{
  "price_max": 300.0,
  "keywords": ["road bike", "fixie"],
  "percent_below_median": 15,
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

Implement the `Source` protocol defined in `deal_sniper/source.py`:

```python
from deal_sniper.listing import Listing

class MyMarketplaceSource:
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

Implement the `Notifier` protocol defined in `deal_sniper/notifier.py`:

```python
from deal_sniper.listing import Listing

class SlackNotifier:
    def __init__(self, webhook_url: str) -> None:
        self._webhook = webhook_url

    def notify(self, listing: Listing, alert_text: str) -> None:
        import urllib.request, json
        body = json.dumps({"text": alert_text}).encode()
        req = urllib.request.Request(self._webhook, data=body,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req)
```

The built-in `ConsoleNotifier` (prints to stdout) is used by default.  Swap it out by passing your
notifier instance to the poller at construction time.
