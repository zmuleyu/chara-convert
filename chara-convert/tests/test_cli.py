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
