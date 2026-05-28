"""Gradio Web UI for chara-convert.

Drag-and-drop character card conversion with gap analysis.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from chara_convert.converter import convert
from chara_convert.diff import analyze
from chara_convert.exporters.markdown import render_markdown
from chara_convert.parser import parse_file
from chara_convert.registry import list_platforms, load_spec


def _do_convert(file_path: str, target_slug: str) -> tuple[str, str, str]:
    """Run conversion and return (gap_summary, converted_fields, markdown_report)."""
    path = Path(file_path)
    spec = load_spec(target_slug)
    card = parse_file(path)
    gap = analyze(card, spec)
    converted = convert(card, spec)
    md = render_markdown(converted, gap)

    # Gap summary as text
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

    # Converted fields as text
    field_lines = []
    for fname in ["name", "description", "personality", "scenario",
                  "first_mes", "mes_example", "system_prompt"]:
        if fname in converted.fields:
            field_lines.append(f"### {fname.replace('_', ' ').title()}")
            field_lines.append(converted.fields[fname])
            field_lines.append("")

    return "\n".join(summary_lines), "\n".join(field_lines), md


def build_app() -> Any:
    """Build and return the Gradio Blocks app."""
    try:
        import gradio as gr  # type: ignore[import-not-found]
    except ImportError:
        raise ImportError(
            "Gradio is required for the Web UI. Install with: uv sync --extra web"
        ) from None

    platforms = list_platforms()

    with gr.Blocks(title="Chara Convert") as app:
        gr.Markdown("# 🎭 Chara Convert — AI Character Card Workbench")
        gr.Markdown("Upload a character card (PNG or JSON) and select a target platform.")

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
                convert_btn = gr.Button("Convert", variant="primary")

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

        # Convert button
        convert_btn.click(
            fn=_do_convert,
            inputs=[file_input, target_select],
            outputs=[gap_output, fields_output, report_output],
        )

        # Download button uses the report text
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
