"""Prompt templates for AI-assisted parser paths.

Each task has its own ``.md`` file loaded via :func:`load_prompt`. Templates
use Python ``str.format`` placeholders (``{name}``); callers pass keyword
arguments matching the placeholders.
"""

from __future__ import annotations

from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


def load_prompt(template_name: str, /, **fields: str) -> str:
    """Load ``<template_name>.md`` from this package and substitute ``{placeholders}``.

    Positional-only first arg so callers can pass a field literally named
    ``name`` (e.g. character name) without collision.

    Raises :class:`FileNotFoundError` if the template is missing.
    """
    path = _PROMPT_DIR / f"{template_name}.md"
    template = path.read_text(encoding="utf-8")
    return template.format(**fields)
