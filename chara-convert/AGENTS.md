# AGENTS.md

## Project Overview
- `chara-convert` is the **AI Character Card Conversion Workbench**.
- Converts and edits AI character cards between platforms (SillyTavern, Janitor AI, Backyard AI, RisuAI, Agnai, etc.).
- Stack: Python 3.11+, Click (CLI), Gradio (Web UI).

## First Steps
- Read `README.md` for architecture overview.
- Check `docs/` for platform spec details.
- Platform specs live in `chara_convert/specs/*.toml`.

## Commands
- `uv sync`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy chara_convert`
- `uv run ccv convert <card> --target <platform> --out report.md`
- `uv run ccv diff <card> --target <platform>`
- `uv run ccv list-platforms`

## Testing And Validation
- Run the smallest relevant validation command after code changes.
- Do not claim completion without a concrete verification step.

## Boundaries
### Always do
- Keep changes scoped to this project.
- Update platform specs in `specs/*.toml` when adding new platform support.
- Mention the exact module in the final summary.

### Ask first
- Adding new production dependencies.
- Changing platform spec schema (TOML structure).

### Never do
- Commit secrets, tokens, or machine-local state files.
- Revert unrelated user changes.
