"""Tests for chara_convert.webui pipeline (Gradio launch not required)."""

from __future__ import annotations

from pathlib import Path

import pytest

from chara_convert.webui import _backend_status_line, _run_pipeline

FIXTURE_CARD = Path(__file__).parent / "fixtures" / "sample_card.json"


def test_run_pipeline_without_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    """ai=False → no ai_filled markers in any output panel."""
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    gap_md, fields_md, full_md, status_md = _run_pipeline(
        str(FIXTURE_CARD), "fictionlab", ai=False
    )
    assert "ai_filled" not in full_md
    assert "ai_filled" not in fields_md
    # Status should reflect that no AI was used (no backend warning either).
    assert "AI not requested" in status_md or "no backend" not in status_md.lower()


def test_run_pipeline_with_ai_mock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """ai=True + CHARA_CONVERT_AI_MOCK → ai_filled appears in the report.

    Uses a minimal card with no scenario/first_mes so enrich_layered's AI
    paths definitely fire (matches CLI test pattern).
    """
    minimal = tmp_path / "minimal.json"
    minimal.write_text(
        '{"name": "Mira", "description": "A thief.", "personality": "quick"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("CHARA_CONVERT_AI_MOCK", "[MOCKED]")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    gap_md, fields_md, full_md, status_md = _run_pipeline(
        str(minimal), "fictionlab", ai=True
    )
    assert "ai_filled" in full_md
    assert "[MOCKED]" in full_md
    assert "mock" in status_md.lower()


def test_run_pipeline_ai_requested_no_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """ai=True but no backend env → status warns, conversion still succeeds."""
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    gap_md, fields_md, full_md, status_md = _run_pipeline(
        str(FIXTURE_CARD), "fictionlab", ai=True
    )
    # No AI was actually applied.
    assert "ai_filled" not in full_md
    # User must be told why.
    assert "no backend" in status_md.lower() or "no ai backend" in status_md.lower()


def test_backend_status_line_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Status line at app start: no env → 'none'."""
    monkeypatch.delenv("CHARA_CONVERT_AI_MOCK", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    line = _backend_status_line()
    assert "none" in line.lower()


def test_backend_status_line_mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Status line at app start: mock env → 'mock' label."""
    monkeypatch.setenv("CHARA_CONVERT_AI_MOCK", "[X]")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    line = _backend_status_line()
    assert "mock" in line.lower()
