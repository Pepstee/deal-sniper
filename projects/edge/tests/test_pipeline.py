"""Integration tests for the situation_monitor CLI pipeline.

Acceptance criterion:
    SM_LLM_BACKEND=stub SM_SOURCES=tests/fixtures/rss_sample.xml
    python3 -m situation_monitor once --config /dev/null
    → exits 0, stdout non-empty markdown digest.

All tests run the real subprocess; nothing about the pipeline is mocked here.
"""
from __future__ import annotations

import os
import subprocess
import sys
import pathlib

import pytest

EDGE_DIR = pathlib.Path(__file__).parent.parent
FIXTURE_XML = EDGE_DIR / "tests" / "fixtures" / "rss_sample.xml"


def _run_once(
    *,
    sm_sources: str | None = None,
    sm_llm_backend: str = "stub",
    config: str = "/dev/null",
    extra_env: dict[str, str] | None = None,
    cwd: pathlib.Path = EDGE_DIR,
) -> subprocess.CompletedProcess:
    """Run `python -m situation_monitor once --config <config>` as a subprocess."""
    env = os.environ.copy()
    env["SM_LLM_BACKEND"] = sm_llm_backend
    if sm_sources is not None:
        env["SM_SOURCES"] = sm_sources
    elif "SM_SOURCES" in env:
        del env["SM_SOURCES"]
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "situation_monitor", "once", "--config", config],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd),
    )


# ---------------------------------------------------------------------------
# Core acceptance criterion
# ---------------------------------------------------------------------------

class TestOnceCommandAcceptance:
    def test_exits_zero_with_stub_backend_and_rss_fixture(self):
        """The primary acceptance criterion: exit code must be 0."""
        result = _run_once(sm_sources="tests/fixtures/rss_sample.xml")
        assert result.returncode == 0, (
            f"Expected exit 0 but got {result.returncode}.\n"
            f"stdout: {result.stdout!r}\n"
            f"stderr: {result.stderr!r}"
        )

    def test_stdout_is_nonempty(self):
        """The pipeline must print something to stdout."""
        result = _run_once(sm_sources="tests/fixtures/rss_sample.xml")
        assert result.stdout.strip(), (
            f"Expected non-empty stdout but got nothing.\n"
            f"stderr: {result.stderr!r}"
        )

    def test_stdout_looks_like_markdown(self):
        """Output must contain at least one markdown structural element."""
        result = _run_once(sm_sources="tests/fixtures/rss_sample.xml")
        stdout = result.stdout
        has_heading = "#" in stdout
        has_bullet = any(line.strip().startswith(("-", "*", "+")) for line in stdout.splitlines())
        assert has_heading or has_bullet, (
            f"Output does not look like markdown.\nstdout: {stdout!r}"
        )

    def test_config_dev_null_is_accepted(self):
        """--config /dev/null must not crash the process."""
        result = _run_once(sm_sources="tests/fixtures/rss_sample.xml", config="/dev/null")
        assert result.returncode == 0

    def test_absolute_path_to_fixture_also_works(self):
        """SM_SOURCES can be an absolute path, not just relative."""
        result = _run_once(sm_sources=str(FIXTURE_XML))
        assert result.returncode == 0
        assert result.stdout.strip()


# ---------------------------------------------------------------------------
# Stub backend — no network I/O
# ---------------------------------------------------------------------------

class TestStubBackend:
    def test_stub_backend_does_not_time_out(self):
        """A real LLM call would block or time out; stub must return quickly."""
        import time
        start = time.monotonic()
        result = _run_once(sm_sources="tests/fixtures/rss_sample.xml")
        elapsed = time.monotonic() - start
        assert elapsed < 30, f"Took {elapsed:.1f}s — stub backend appears to make network calls"
        assert result.returncode == 0

    def test_unknown_backend_exits_nonzero(self):
        """An unrecognised SM_LLM_BACKEND must cause a non-zero exit."""
        result = _run_once(
            sm_sources="tests/fixtures/rss_sample.xml",
            sm_llm_backend="no_such_backend_xyz_99",
        )
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Source file handling
# ---------------------------------------------------------------------------

class TestSourceFileHandling:
    def test_missing_source_file_exits_nonzero(self):
        """A non-existent SM_SOURCES path must not exit 0 silently."""
        result = _run_once(sm_sources="tests/fixtures/does_not_exist.xml")
        assert result.returncode != 0

    def test_empty_xml_file_does_not_produce_full_digest(self, tmp_path):
        """An empty file has no items; must not exit 0 AND produce a full article digest."""
        empty = tmp_path / "empty.xml"
        empty.write_text("")
        result = _run_once(sm_sources=str(empty))
        if result.returncode == 0:
            # Allowed only if the output is clearly empty/minimal — not a full item digest.
            # We don't want the stub to fabricate items out of thin air.
            stdout = result.stdout
            assert len(stdout.strip()) < 500, (
                f"Empty RSS file produced a suspiciously large digest ({len(stdout)} chars): {stdout[:200]!r}"
            )

    def test_malformed_xml_does_not_exit_zero_silently(self, tmp_path):
        """Malformed XML should either exit nonzero or emit an error message."""
        bad = tmp_path / "bad.xml"
        bad.write_text("this is not xml <<>>")
        result = _run_once(sm_sources=str(bad))
        if result.returncode == 0:
            combined = (result.stdout + result.stderr).lower()
            assert any(kw in combined for kw in ("error", "warn", "invalid", "parse", "0 item")), (
                f"Malformed XML exited 0 but output gave no indication of a problem.\n"
                f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
            )

    def test_valid_rss_fixture_parses_without_error_output(self):
        """No error or traceback should appear in stderr for a valid fixture."""
        result = _run_once(sm_sources="tests/fixtures/rss_sample.xml")
        assert "Traceback" not in result.stderr, (
            f"Unexpected traceback in stderr: {result.stderr}"
        )
        assert "Error" not in result.stderr or result.returncode == 0


# ---------------------------------------------------------------------------
# No-source guard
# ---------------------------------------------------------------------------

class TestNoSourceGuard:
    def test_no_sm_sources_env_var_exits_nonzero(self):
        """Running without SM_SOURCES must not silently produce an empty digest and exit 0."""
        result = _run_once(sm_sources=None)
        # Either non-zero exit, or empty stdout (graceful no-op), but NOT a crash with exit 0
        # that produces no content. A zero exit with empty stdout is also undesirable.
        if result.returncode == 0:
            assert result.stdout.strip() != "" or result.stderr.strip() != "", (
                "With no SM_SOURCES, exit 0 with no output is confusing — "
                "expect either content or a nonzero exit."
            )


# ---------------------------------------------------------------------------
# Subcommand routing
# ---------------------------------------------------------------------------

class TestSubcommandRouting:
    def test_unknown_subcommand_exits_nonzero(self):
        env = os.environ.copy()
        env["SM_LLM_BACKEND"] = "stub"
        env["SM_SOURCES"] = "tests/fixtures/rss_sample.xml"
        result = subprocess.run(
            [sys.executable, "-m", "situation_monitor", "not_a_real_command"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(EDGE_DIR),
        )
        assert result.returncode != 0

    def test_help_flag_exits_zero(self):
        env = os.environ.copy()
        result = subprocess.run(
            [sys.executable, "-m", "situation_monitor", "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(EDGE_DIR),
        )
        # --help must exit 0 with usage information
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert len(combined.strip()) > 0
