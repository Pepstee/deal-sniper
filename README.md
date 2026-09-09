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

## Source access

Bundled fixtures support offline verification. `HttpSource` accepts an explicit
HTTP(S) endpoint and parses the supported generic JSON or HTML listing formats.
It is not a verified adapter for any live marketplace. Use endpoints you are
authorised to access. The recovered Craigslist helper only constructs a URL;
it does not fetch data or establish marketplace compatibility.

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

Create a deterministic starter configuration locally:

```
deal-sniper config-init --output config.json
```

This command only writes the requested JSON file. It does not open a marketplace, create the
SQLite seen-listing database, or make a network request. Existing legacy invocations without a
subcommand remain supported.

List the persisted seen listing identities from the configured SQLite database:

```
deal-sniper list-seen --config config.json
```

The command prints one URL per line in stable lexical order and performs no source fetch.

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


## Recovered capabilities

Single-query invocations remain supported. For an explicit generic HTTP endpoint,
use `--source http --url URL --format json` (or `html`). Requests have a finite
timeout. Parsers support list/div/table HTML and JSON lists or individual records;
malformed rows are skipped while invalid whole documents fail visibly.

`Listing` retains optional source ID, timestamp and raw payload. The SQLite store
keeps complete first-seen records alongside URL deduplication. Existing URL-only
rows survive the additive upgrade; missing historic metadata remains unknown.
`deal-sniper list-listings --config config.json` exports captured records as JSON.
`MedianTracker.history(query)` returns a copy of process-local observations.

Optional configuration fields are `keyword_mode` (`all`, default, or `any`),
`median_mode` (`sequential`, default, or `batch`), and
`deduplicate_observations` (default `false`). Batch mode evaluates listings against
the complete poll median. Observation deduplication avoids repeatedly recording
the same seen URL. These options retain the differing donor behaviours explicitly.
`below_median_pct` always means a minimum discount. The old inverted
`max_percent_below_median` rule is intentionally replaced, not silently aliased.

Multiple queries share a fair scheduler with independent intervals, median
keys and per-query URL deduplication. A rejection in one query cannot suppress a
match in another. Global listing inspection retains the first observed record. Every query runs once per requested iteration:

```json
{
  "db_path": "deals.db",
  "queries": [
    {"name": "bicycles", "source_type": "local", "source_path": "fixtures/sample.json",
     "search_term": "bicycle", "poll_interval_sec": 300, "rules": {"max_price": 300}},
    {"name": "cameras", "source_type": "local", "source_path": "fixtures/sample.json",
     "search_term": "camera", "poll_interval_sec": 600, "rules": {"max_price": 200}}
  ]
}
```

Run it with `deal-sniper --config config.json --iterations 1`. Source search text
and per-query rules are distinct; local fixtures are replayed as supplied.
Interrupting polling closes the database cleanly. Notification remains console
output or a caller-supplied notifier; migration does not activate external alerts.

## Reconciliation and package boundary

Compared canonical `a8fe3e8` with the three archived copies `c4cf12a`, `79d5f8f`
and `41250bb`. Recovered useful source formats, HTTP loading, full listing metadata,
history access, rule modes, bounded count reporting and multi-query scheduling in
the existing owners. Old class/module names and nonworking empty-source CLI paths
are replaced by the canonical API and executable CLI. Original Mac copies remain.

`projects/edge` is a retained historical Situation Monitor fragment, not part of
the Deal Sniper package. Its seven CLI tests fail because its CLI implementation
is absent. It remains separately inspectable; it is neither installed nor counted
as Deal Sniper verification. Default pytest collection is scoped to `tests`.
Its threshold-alert helper overlaps the canonical Situation Monitor alert owner.
No historical files were deleted or represented as a working application.

The package build backend is repaired and package discovery includes only
`deal_sniper`. Verification covers the installed CLI, local fixtures, synthetic
SQLite restarts and loopback HTTP. It makes no live marketplace or external
notification claim. The code graph is refreshed; document semantics remain partial.
