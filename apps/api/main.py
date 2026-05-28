from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import platforms, parse, convert

app = FastAPI(title="chara-convert shim", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://studio.aichathub.uk", "http://localhost:4321"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Creem-Token"],
)

app.include_router(platforms.router, prefix="/api")
app.include_router(parse.router, prefix="/api")
app.include_router(convert.router, prefix="/api")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
