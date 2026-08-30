"""CLI argument parsing: correct namespace for all flags and required-arg enforcement."""
import argparse
import json
import sys
from pathlib import Path

import pytest

from deal_sniper.config import Config, default_config

FIXTURES = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Minimal mirror of the CLI parser — tests the expected interface without
# importing main() so parse-only assertions don't spin up the full pipeline.
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """Mirror of deal_sniper.cli's ArgumentParser setup."""
    parser = argparse.ArgumentParser(description="Deal Sniper — find below-median listings")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    parser.add_argument("--source", required=True, help="Source name (e.g. mock_html, mock_json)")
    parser.add_argument("--fixture", help="Path to fixture file (HTML or JSON) for mock sources")
    parser.add_argument(
        "--iterations", type=int, default=None,
        help="Number of poll iterations (default: run forever)",
    )
    return parser


class TestArgparseNamespace:
    def test_all_flags_produce_correct_namespace(self):
        ns = _build_parser().parse_args([
            "--config", "conf.json",
            "--source", "mock_html",
            "--fixture", "data.html",
            "--iterations", "3",
        ])
        assert ns.config == "conf.json"
        assert ns.source == "mock_html"
        assert ns.fixture == "data.html"
        assert ns.iterations == 3

    def test_fixture_defaults_to_none(self):
        ns = _build_parser().parse_args(["--config", "c.json", "--source", "s"])
        assert ns.fixture is None

    def test_iterations_defaults_to_none(self):
        ns = _build_parser().parse_args(["--config", "c.json", "--source", "s"])
        assert ns.iterations is None

    def test_iterations_is_coerced_to_int(self):
        ns = _build_parser().parse_args([
            "--config", "c.json", "--source", "s", "--iterations", "10",
        ])
        assert isinstance(ns.iterations, int)
        assert ns.iterations == 10

    def test_iterations_zero_is_valid(self):
        ns = _build_parser().parse_args([
            "--config", "c.json", "--source", "s", "--iterations", "0",
        ])
        assert ns.iterations == 0

    def test_source_value_stored_verbatim(self):
        ns = _build_parser().parse_args(["--config", "c.json", "--source", "mock_json"])
        assert ns.source == "mock_json"

    def test_config_path_stored_verbatim(self):
        ns = _build_parser().parse_args(["--config", "/some/path/config.json", "--source", "s"])
        assert ns.config == "/some/path/config.json"


class TestRequiredArgs:
    def test_missing_config_raises_systemexit(self):
        with pytest.raises(SystemExit) as exc_info:
            _build_parser().parse_args(["--source", "mock_json"])
        assert exc_info.value.code != 0

    def test_missing_source_raises_systemexit(self):
        with pytest.raises(SystemExit) as exc_info:
            _build_parser().parse_args(["--config", "conf.json"])
        assert exc_info.value.code != 0

    def test_no_args_raises_systemexit(self):
        with pytest.raises(SystemExit) as exc_info:
            _build_parser().parse_args([])
        assert exc_info.value.code != 0

    def test_unknown_flag_raises_systemexit(self):
        with pytest.raises(SystemExit) as exc_info:
            _build_parser().parse_args([
                "--config", "c.json", "--source", "s", "--bogus",
            ])
        assert exc_info.value.code != 0

    def test_non_integer_iterations_raises_systemexit(self):
        with pytest.raises(SystemExit) as exc_info:
            _build_parser().parse_args([
                "--config", "c.json", "--source", "s", "--iterations", "not_a_number",
            ])
        assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# Integration: main() with real files, zero iterations (no blocking sleep)
# ---------------------------------------------------------------------------

def _write_config(path: Path, db_path: str = ":memory:", **overrides) -> Path:
    data = {
        "price_max": 300.0,
        "keywords": [],
        "below_median_pct": 0.0,
        "poll_interval_s": 0,
        "db_path": db_path,
    }
    data.update(overrides)
    config_file = path / "config.json"
    config_file.write_text(json.dumps(data))
    return config_file


class TestCLIIntegration:
    def test_config_init_writes_deterministic_loadable_local_config(
        self, capsys, tmp_path
    ):
        output = tmp_path / "generated.json"
        from deal_sniper.cli import main

        main(["config-init", "--output", str(output)])
        first = output.read_bytes()
        main(["config-init", "--output", str(output)])

        assert output.read_bytes() == first
        assert json.loads(first) == default_config()
        assert Config.from_dict(json.loads(first)) == Config.from_dict(default_config())
        assert capsys.readouterr().out.splitlines() == [
            f"Config written to {output}",
            f"Config written to {output}",
        ]
        assert not (tmp_path / "deals.db").exists()

    def test_config_init_requires_explicit_output(self):
        from deal_sniper.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["config-init"])
        assert exc_info.value.code == 2

    def test_main_with_json_fixture_zero_iterations(self, monkeypatch, tmp_path):
        config_file = _write_config(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "deal-sniper",
            "--config", str(config_file),
            "--source", "mock_json",
            "--fixture", str(FIXTURES / "sample.json"),
            "--iterations", "0",
        ])
        from deal_sniper.cli import main
        main()  # must not raise

    def test_main_with_html_fixture_zero_iterations(self, monkeypatch, tmp_path):
        config_file = _write_config(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "deal-sniper",
            "--config", str(config_file),
            "--source", "mock_html",
            "--fixture", str(FIXTURES / "sample.html"),
            "--iterations", "0",
        ])
        from deal_sniper.cli import main
        main()

    def test_main_with_json_fixture_one_iteration(self, monkeypatch, tmp_path):
        config_file = _write_config(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "deal-sniper",
            "--config", str(config_file),
            "--source", "mock_json",
            "--fixture", str(FIXTURES / "sample.json"),
            "--iterations", "1",
        ])
        from deal_sniper.cli import main
        main()

    def test_main_applies_optional_filters_to_offline_fixture(
        self, capsys, monkeypatch, tmp_path
    ):
        config_file = _write_config(
            tmp_path,
            min_price=50.0,
            exclude_keywords=["SOFA"],
        )
        monkeypatch.setattr(sys, "argv", [
            "deal-sniper",
            "--config", str(config_file),
            "--source", "mock_json",
            "--fixture", str(FIXTURES / "sample.json"),
            "--iterations", "1",
        ])
        from deal_sniper.cli import main
        main()
        output = capsys.readouterr().out
        assert "Trek Mountain Bike 2021" in output
        assert "Vintage Leather Sofa" not in output
        assert "Standing Desk Lamp" not in output
        assert "Cast Iron Skillet 12in" not in output

    def test_main_without_fixture_raises_systemexit(self, monkeypatch, tmp_path):
        config_file = _write_config(tmp_path)
        monkeypatch.setattr(sys, "argv", [
            "deal-sniper",
            "--config", str(config_file),
            "--source", "unknown_source",
        ])
        from deal_sniper.cli import main
        with pytest.raises(SystemExit):
            main()
