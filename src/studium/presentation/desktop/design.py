"""Studium's visual tokens, in logical pixels, shared by both themes."""

from dataclasses import dataclass

SPACES = {"xs": 4, "s": 8, "m": 12, "l": 20, "xl": 32}
RADII = {"control": 8, "surface": 11}
TYPE = {"page": 28, "section": 19, "body": 13, "secondary": 13, "caption": 12, "table": 13}


@dataclass(frozen=True)
class Colors:
    background: str
    navigation: str
    surface: str
    secondary: str
    elevated: str
    text: str
    muted: str
    border: str
    hover: str
    selected: str
    accent: str
    accent_hover: str
    on_accent: str
    disabled: str
    success: str
    warning: str
    error: str
    information: str


LIGHT = Colors(
    "#f7faff",
    "#f2f6fc",
    "#ffffff",
    "#f4f7fc",
    "#ffffff",
    "#1c304a",
    "#596c83",
    "#e2e9f2",
    "#edf4fc",
    "#e0efff",
    "#246ed1",
    "#1d5fb9",
    "#ffffff",
    "#8a919f",
    "#2f7963",
    "#986c21",
    "#b04d53",
    "#246ed1",
)
DARK = Colors(
    "#1e252e",
    "#222b35",
    "#26313d",
    "#2b3744",
    "#2d3946",
    "#edf0f7",
    "#a8afbf",
    "#3c4a5a",
    "#344252",
    "#304a67",
    "#83b6f6",
    "#9dc7fb",
    "#122237",
    "#7c8495",
    "#82c4ab",
    "#d6b36f",
    "#ea9399",
    "#9aafea",
)


def colors(theme):
    return DARK if theme == "dark" else LIGHT
