"""Click CLI entry point for chara-convert."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from chara_convert.converter import convert
from chara_convert.diff import analyze
from chara_convert.exporters.markdown import render_markdown
from chara_convert.parser import parse_file
from chara_convert.registry import list_platforms, load_spec


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """Chara Convert — AI Character Card Conversion Workbench."""
    pass


@main.command("convert")
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option("--target", "-t", required=True, help="Target platform slug")
@click.option("--out", "-o", type=click.Path(path_type=Path), help="Output markdown file")
def convert_cmd(source: Path, target: str, out: Path | None) -> None:
    """Convert a character card and produce a gap analysis report."""
    try:
        spec = load_spec(target)
    except FileNotFoundError:
        available = ", ".join(list_platforms())
        click.echo(f"Unknown target '{target}'. Available: {available}", err=True)
        sys.exit(1)

    try:
        card = parse_file(source)
    except ValueError as e:
        click.echo(f"Parse error: {e}", err=True)
        sys.exit(1)

    gap = analyze(card, spec)
    converted = convert(card, spec)
    md = render_markdown(converted, gap)

    if out:
        out.write_text(md, encoding="utf-8")
        click.echo(f"Report written to {out}")
    else:
        click.echo(md)

    click.echo(f"\nReady score: {gap.ready_score}/100", err=True)
    if gap.missing:
        click.echo(f"Missing: {', '.join(gap.missing)}", err=True)
    if gap.unsupported:
        click.echo(f"Unsupported (dropped): {', '.join(gap.unsupported)}", err=True)


@main.command("diff")
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option("--target", "-t", required=True, help="Target platform slug")
def diff_cmd(source: Path, target: str) -> None:
    """Show a terminal gap analysis without producing a report."""
    try:
        spec = load_spec(target)
    except FileNotFoundError:
        available = ", ".join(list_platforms())
        click.echo(f"Unknown target '{target}'. Available: {available}", err=True)
        sys.exit(1)

    try:
        card = parse_file(source)
    except ValueError as e:
        click.echo(f"Parse error: {e}", err=True)
        sys.exit(1)

    gap = analyze(card, spec)
    click.echo(f"Target: {gap.target_name}")
    click.echo(f"Ready score: {gap.ready_score}/100")
    if gap.perfect_match:
        click.echo(f"Perfect match: {', '.join(gap.perfect_match)}")
    if gap.renamed:
        pairs = ", ".join(f"{s} → {t}" for s, t in gap.renamed)
        click.echo(f"Renamed: {pairs}")
    if gap.missing:
        click.echo(f"Missing: {', '.join(gap.missing)}")
    if gap.unsupported:
        click.echo(f"Unsupported: {', '.join(gap.unsupported)}")
    if gap.truncated:
        pairs = ", ".join(f"{f} ({a}/{lim})" for f, a, lim in gap.truncated)
        click.echo(f"Truncated: {pairs}")
    if gap.notes:
        click.echo("\nNotes:")
        for note in gap.notes:
            click.echo(f"  - {note}")


@main.command("list-platforms")
def list_platforms_cmd() -> None:
    """List available target platforms."""
    for slug in list_platforms():
        spec = load_spec(slug)
        click.echo(f"{slug:20s}  {spec.name}")


@main.command("webui")
@click.option("--port", "-p", default=7860, help="Port to run Gradio on")
@click.option("--share", is_flag=True, help="Create a public Gradio share link")
def webui_cmd(port: int, share: bool) -> None:
    """Launch the Gradio Web UI."""
    try:
        from chara_convert.webui import build_app
    except ImportError:
        click.echo(
            "Web UI dependencies not installed. Run: uv sync --extra web",
            err=True,
        )
        sys.exit(1)

    app = build_app()
    app.launch(server_port=port, share=share)
