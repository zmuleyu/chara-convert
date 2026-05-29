from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import platforms, parse, convert, ai_enrich

app = FastAPI(title="chara-convert shim", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    # Keep aligned with workers/billing/src/index.ts ALLOWED_ORIGINS so a single
    # browser session can talk to both backends without dual-allow-list pain.
    allow_origins=[
        "https://studio.aichathub.uk",
        "https://chara-convert-web.pages.dev",
        "http://localhost:4321",
        "http://127.0.0.1:4321",
    ],
    allow_methods=["GET", "POST"],
    # X-User-Id is required as of Phase C (OR credit router): AiAssistPanel
    # sends it on /ai/enrich so the FastAPI handler can route hold/debit/refund
    # through the billing Worker. Without it on the allow-list, the browser's
    # preflight fails and the actual POST never goes — visible as "Failed to
    # fetch" in the panel, which the apps/web E2E tripped on first run.
    allow_headers=["Content-Type", "X-Creem-Token", "X-User-Id"],
)

app.include_router(platforms.router, prefix="/api")
app.include_router(parse.router, prefix="/api")
app.include_router(convert.router, prefix="/api")
app.include_router(ai_enrich.router, prefix="/api")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
