from __future__ import annotations
from typing import Literal, TypedDict

from fastapi import APIRouter

from chara_convert.registry import list_platforms, load_spec
from chara_convert.sources.auto import CAIParser, ChaiParser, PolyBuzzParser

router = APIRouter()


class SourceEntry(TypedDict):
    slug: str
    name: str
    kind: Literal["file", "paste"]


class TargetEntry(TypedDict):
    slug: str
    name: str


_FILE_SOURCES: tuple[SourceEntry, ...] = (
    {"slug": "sillytavern_v2", "name": "SillyTavern v2 (PNG/JSON)", "kind": "file"},
    {"slug": "risuai", "name": "RisuAI", "kind": "file"},
    {"slug": "agnai", "name": "Agnai", "kind": "file"},
    {"slug": "novelai", "name": "NovelAI", "kind": "file"},
    {"slug": "saucepan", "name": "Saucepan", "kind": "file"},
)


# Hand-curated display names for paste parsers (slug -> name)
_PASTE_DISPLAY: dict[str, str] = {
    "character_ai": "Character.AI (paste)",
    "chai": "Chai (paste)",
    "polybuzz": "PolyBuzz (paste)",
}


def _paste_sources() -> list[SourceEntry]:
    out: list[SourceEntry] = []
    for parser_cls in (CAIParser, ChaiParser, PolyBuzzParser):
        slug = parser_cls().slug
        out.append({"slug": slug, "name": _PASTE_DISPLAY.get(slug, slug), "kind": "paste"})
    return out


def _targets() -> list[TargetEntry]:
    out: list[TargetEntry] = []
    for slug in list_platforms():
        spec = load_spec(slug)
        out.append({"slug": slug, "name": spec.name})
    return out


@router.get("/platforms")
def platforms() -> dict[str, list[SourceEntry] | list[TargetEntry]]:
    return {
        "sources": [*_FILE_SOURCES, *_paste_sources()],
        "targets": _targets(),
    }
