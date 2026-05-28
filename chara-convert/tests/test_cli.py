"""Tests for chara_convert.cli."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from chara_convert.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_list_platforms() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["list-platforms"])
    assert result.exit_code == 0
    assert "janitorai" in result.output
    assert "sillytavern_v2" in result.output


def test_diff() -> None:
    runner = CliRunner()
    result = runner.invoke(main, [
        "diff", str(FIXTURES / "sample_card.json"),
        "--target", "janitorai",
    ])
    assert result.exit_code == 0
    assert "Ready score:" in result.output
    assert "Janitor AI" in result.output


def test_convert_stdout() -> None:
    runner = CliRunner()
    result = runner.invoke(main, [
        "convert", str(FIXTURES / "sample_card.json"),
        "--target", "janitorai",
    ])
    assert result.exit_code == 0
    assert "Aria Nightshade" in result.output
    assert "Ready score:" in result.output


def test_convert_unknown_target() -> None:
    runner = CliRunner()
    result = runner.invoke(main, [
        "convert", str(FIXTURES / "sample_card.json"),
        "--target", "notaplatform",
    ])
    assert result.exit_code != 0
    assert "Unknown target" in result.output


def test_convert_file_not_found() -> None:
    runner = CliRunner()
    result = runner.invoke(main, [
        "convert", str(FIXTURES / "does_not_exist.json"),
        "--target", "janitorai",
    ])
    assert result.exit_code != 0
    assert "File not found" in result.output or "does not exist" in result.output


def test_convert_ai_flag_with_mock_backend(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """--ai uses CHARA_CONVERT_AI_MOCK as a canned response when set."""
    # Minimal card with no mes_example / scenario so AI enrichment actually fires.
    fx = tmp_path / "minimal.json"
    fx.write_text(
        '{"name": "Mira", "description": "A thief.", "first_mes": "Hi.", '
        '"personality": "quick"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("CHARA_CONVERT_AI_MOCK", "[MOCKED AI OUTPUT]")
    runner = CliRunner()
    result = runner.invoke(main, [
        "convert", str(fx),
        "--target", "fictionlab",
        "--ai",
    ])
    assert result.exit_code == 0, result.output
    assert "[MOCKED AI OUTPUT]" in result.output


def test_convert_ai_flag_without_backend_errors(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """--ai with neither mock nor ANTHROPIC_API_KEY env exits non-zero."""
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    runner = CliRunner()
    result = runner.invoke(main, [
        "convert", str(FIXTURES / "sample_card.json"),
        "--target", "fictionlab",
        "--ai",
    ])
    assert result.exit_code != 0
    assert "no AI backend" in result.output or "ANTHROPIC_API_KEY" in result.output


def test_convert_no_ai_flag_unchanged() -> None:
    """Without --ai, behavior is identical to pre-PR4 (heuristic path)."""
    runner = CliRunner()
    result = runner.invoke(main, [
        "convert", str(FIXTURES / "sample_card.json"),
        "--target", "fictionlab",
    ])
    assert result.exit_code == 0
    # Heuristic-only run does NOT emit ai_filled lines.
    assert "ai_filled" not in result.output
