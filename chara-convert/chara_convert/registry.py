"""Platform specification registry."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FieldSpec:
    name: str
    required: bool = False
    max_chars: int = 0  # 0 = unlimited
    type: str = "text"
    aliases: list[str] = field(default_factory=list)
    native: bool = True  # false = not natively supported (may be dropped or merged)


@dataclass
class LorebookSpec:
    supported: bool = False
    entry_fields: list[str] = field(default_factory=list)
    recursive_scanning: bool = False


@dataclass
class GreetingSpec:
    multiple: bool = False
    max_count: int = 0


@dataclass
class DialogueSpec:
    formats: list[str] = field(default_factory=list)
    preferred: str = "Plain"


@dataclass
class LayerSpec:
    """A single layer inside a layered platform (e.g. FictionLab character/scenario/location/lore)."""

    name: str
    fields: dict[str, FieldSpec] = field(default_factory=dict)


@dataclass
class PlatformSpec:
    name: str
    slug: str
    version: int = 1
    fields: dict[str, FieldSpec] = field(default_factory=dict)
    lorebook: LorebookSpec = field(default_factory=LorebookSpec)
    greeting: GreetingSpec = field(default_factory=GreetingSpec)
    example_dialogue: DialogueSpec = field(default_factory=DialogueSpec)
    notes: dict[str, str] = field(default_factory=dict)
    # Layered platforms (FictionLab) declare [layers.*] in TOML. None for flat specs.
    layers: dict[str, LayerSpec] | None = None

    def field_names(self) -> set[str]:
        return set(self.fields.keys())

    def has_field(self, name: str) -> bool:
        if name in self.fields:
            return True
        return any(name in f.aliases for f in self.fields.values())

    def get_field(self, name: str) -> FieldSpec | None:
        if name in self.fields:
            return self.fields[name]
        for f in self.fields.values():
            if name in f.aliases:
                return f
        return None


def _build_field(fname: str, fdata: dict[str, Any]) -> FieldSpec:
    return FieldSpec(
        name=fname,
        required=fdata.get("required", False),
        max_chars=fdata.get("max_chars", 0),
        type=fdata.get("type", "text"),
        aliases=fdata.get("aliases", []),
        native=fdata.get("native", True),
    )


def _load_spec_from_dict(data: dict[str, Any]) -> PlatformSpec:
    spec = PlatformSpec(
        name=data["name"],
        slug=data["slug"],
        version=data.get("version", 1),
        notes=data.get("notes", {}),
    )

    # Fields (flat)
    for fname, fdata in data.get("fields", {}).items():
        spec.fields[fname] = _build_field(fname, fdata)

    # Layers (nested platforms like FictionLab)
    layers_data = data.get("layers")
    if isinstance(layers_data, dict) and layers_data:
        layers: dict[str, LayerSpec] = {}
        for lname, ldata in layers_data.items():
            layer = LayerSpec(name=lname)
            for fname, fdata in ldata.get("fields", {}).items():
                layer.fields[fname] = _build_field(fname, fdata)
            layers[lname] = layer
        spec.layers = layers

    # Lorebook
    lb = data.get("lorebook", {})
    spec.lorebook = LorebookSpec(
        supported=lb.get("supported", False),
        entry_fields=lb.get("entry_fields", []),
        recursive_scanning=lb.get("recursive_scanning", False),
    )

    # Greeting
    gr = data.get("greeting", {})
    spec.greeting = GreetingSpec(
        multiple=gr.get("multiple", False),
        max_count=gr.get("max_count", 0),
    )

    # Example dialogue
    ed = data.get("example_dialogue", {})
    spec.example_dialogue = DialogueSpec(
        formats=ed.get("formats", ["Plain"]),
        preferred=ed.get("preferred", "Plain"),
    )

    return spec


def load_spec(slug: str) -> PlatformSpec:
    """Load a platform spec by slug (e.g. 'sillytavern', 'janitorai')."""
    here = Path(__file__).parent / "specs"
    path = here / f"{slug}.toml"
    if not path.exists():
        raise FileNotFoundError(f"Platform spec not found: {slug} (looked in {path})")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return _load_spec_from_dict(data)


def list_platforms() -> list[str]:
    """Return list of available platform spec slugs."""
    here = Path(__file__).parent / "specs"
    return sorted(p.stem for p in here.glob("*.toml"))
