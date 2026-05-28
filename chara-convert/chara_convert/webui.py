"""Gradio Web UI for chara-convert.

Drag-and-drop character card conversion with gap analysis. AI enrichment is
opt-in via the ``--ai`` checkbox; backend resolves through the same env-var
precedence the CLI uses (see :mod:`chara_convert.llm.factory`).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from chara_convert.ai import enrich_layered
from chara_convert.converter import convert
from chara_convert.diff import analyze
from chara_convert.exporters.markdown import render_markdown
from chara_convert.llm.factory import build_ai_client_or_none
from chara_convert.parser import parse_file
from chara_convert.registry import list_platforms, load_spec

_STATUS_LABELS = {
    "mock": "🧪 Backend: **mock** — using CHARA_CONVERT_AI_MOCK canned response",
    "anthropic": "🤖 Backend: **anthropic** — using ANTHROPIC_API_KEY",
    "none": "⚪ Backend: **none** — set CHARA_CONVERT_AI_MOCK or ANTHROPIC_API_KEY to enable AI",
}


def _backend_status_line() -> str:
    """Human-readable backend label for the app header (computed at app build)."""
    _client, status = build_ai_client_or_none()
    return _STATUS_LABELS.get(status, f"Backend: {status}")


def _run_pipeline(
    file_path: str, target_slug: str, ai: bool
) -> tuple[str, str, str, str]:
    """Pure pipeline used by both the Gradio callback and tests.

    Returns ``(gap_summary_md, converted_fields_md, full_report_md,
    run_status_md)``. ``run_status_md`` reports what actually happened with
    the AI request — useful when the user checks the box but no backend is
    configured (we don't crash; we surface why nothing changed).
    """
    path = Path(file_path)
    spec = load_spec(target_slug)
    card = parse_file(path)
    gap = analyze(card, spec)
    converted = convert(card, spec)

    if ai:
        client, status = build_ai_client_or_none()
        if client is None:
            run_status = (
                "⚠️ AI requested but no backend configured — ran heuristic only. "
                "Set CHARA_CONVERT_AI_MOCK or ANTHROPIC_API_KEY."
            )
        else:
            enrich_layered(converted, card, client=client)
            run_status = f"✅ AI enrichment applied via **{status}** backend."
    else:
        run_status = "AI not requested (heuristic-only conversion)."

    md = render_markdown(converted, gap)

    summary_lines = [
        f"**Target:** {gap.target_name}",
        f"**Ready Score:** {gap.ready_score}/100",
        "",
    ]
    if gap.perfect_match:
        summary_lines.append(f"✅ Perfect match: {', '.join(gap.perfect_match)}")
    if gap.renamed:
        pairs = ", ".join(f"{s} → {t}" for s, t in gap.renamed)
        summary_lines.append(f"🔄 Renamed: {pairs}")
    if gap.missing:
        summary_lines.append(f"❌ Missing: {', '.join(gap.missing)}")
    if gap.unsupported:
        summary_lines.append(f"⚠️ Unsupported: {', '.join(gap.unsupported)}")
    if gap.truncated:
        pairs = ", ".join(f"{f} ({a} > {lim})" for f, a, lim in gap.truncated)
        summary_lines.append(f"✂️ Truncated: {pairs}")
    if gap.notes:
        summary_lines.append("")
        summary_lines.append("**Notes:**")
        for note in gap.notes:
            summary_lines.append(f"- {note}")

    field_lines = []
    for fname in ["name", "description", "personality", "scenario",
                  "first_mes", "mes_example", "system_prompt"]:
        if fname in converted.fields:
            field_lines.append(f"### {fname.replace('_', ' ').title()}")
            field_lines.append(converted.fields[fname])
            field_lines.append("")

    return "\n".join(summary_lines), "\n".join(field_lines), md, run_status


def build_app() -> Any:
    """Build and return the Gradio Blocks app."""
    try:
        import gradio as gr  # type: ignore[import-untyped]
    except ImportError:
        raise ImportError(
            "Gradio is required for the Web UI. Install with: uv sync --extra web"
        ) from None

    platforms = list_platforms()
    initial_status = _backend_status_line()

    with gr.Blocks(title="Chara Convert") as app:
        gr.Markdown("# 🎭 Chara Convert — AI Character Card Workbench")
        gr.Markdown("Upload a character card (PNG or JSON) and select a target platform.")
        gr.Markdown(initial_status)

        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(
                    label="Character Card",
                    file_types=[".png", ".json"],
                )
                target_select = gr.Dropdown(
                    label="Target Platform",
                    choices=platforms,
                    value=platforms[0] if platforms else None,
                )
                ai_checkbox = gr.Checkbox(
                    label="🤖 Use AI to fill missing layered fields",
                    value=False,
                    info="Fills example_dialogue / scenario_intro when missing. "
                    "Requires CHARA_CONVERT_AI_MOCK or ANTHROPIC_API_KEY.",
                )
                convert_btn = gr.Button("Convert", variant="primary")
                run_status_output = gr.Markdown(label="Run Status")

            with gr.Column(scale=2):
                with gr.Tab("Gap Analysis"):
                    gap_output = gr.Markdown(label="Analysis")
                with gr.Tab("Converted Fields"):
                    fields_output = gr.Markdown(label="Fields")
                with gr.Tab("Full Report"):
                    report_output = gr.TextArea(
                        label="Markdown Report",
                        lines=20,
                        interactive=True,
                    )
                    download_btn = gr.DownloadButton(
                        label="Download Report",
                        variant="secondary",
                    )

        convert_btn.click(
            fn=_run_pipeline,
            inputs=[file_input, target_select, ai_checkbox],
            outputs=[gap_output, fields_output, report_output, run_status_output],
        )

        def _make_download(report_text: str) -> str:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(report_text)
                return tmp.name

        download_btn.click(
            fn=_make_download,
            inputs=[report_output],
            outputs=[download_btn],
        )

    return app
