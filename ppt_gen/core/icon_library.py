"""icon_library.py — Phase E icon resolution.

Maps a small vocabulary of icon names (chosen by the LLM from an enum) to
bundled 256x256 monochrome PNG files. Icons ship in pure black on transparent
background; ``resolve_icon()`` recolors them to the requested theme accent so
the same icon set works across light/dark/navy themes.

The LLM is never asked to produce icon bytes or paths — only a categorical
name from ``ICON_NAMES``. ``resolve_icon()`` returns None for unknown/missing
icons so the renderer can degrade gracefully (skip the picture).
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image

logger = logging.getLogger("icon_library")

# Directory holding bundled monochrome PNG icons.
_ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"

# Curated icon vocabulary exposed to the LLM. Keys are the canonical names
# the LLM may pick; values are the on-disk filenames (without extension).
ICON_MAP: Dict[str, str] = {
    "trend_up":      "trend_up",
    "trend_down":    "trend_down",
    "target":        "target",
    "users":         "users",
    "shield":        "shield_check",
    "chart_bar":     "chart_bar",
    "chart_pie":     "chart_pie",
    "dollar":        "dollar",
    "rupee":         "rupee",
    "percent":       "percent",
    "check":         "check_circle",
    "alert":         "alert",
    "lightbulb":     "lightbulb",
    "building":      "building",
    "award":         "award",
    "briefcase":     "briefcase",
    "flag":          "flag",
    "calendar":      "calendar",
    "layers":        "layers",
    "map_pin":       "map_pin",
    "clock":         "clock",
    "coins":         "coins",
    "zap":           "zap",
    "star":          "star",
    "branch":        "git_branch",
    "download":      "download",
    "refresh":       "refresh",
    "search":        "search",
    "settings":      "settings",
    "thumbs_up":     "thumbs_up",
    # Phase 3 expansion: 20 new icons
    "globe":         "globe",
    "database":      "database",
    "arrow_right":   "arrow_right",
    "file_text":     "file_text",
    "bar_chart_2":   "bar_chart_2",
    "trending_up":   "trending_up",
    "shield_plus":   "shield_plus",
    "grid":          "grid",
    "package":       "package",
    "message":       "message_circle",
    "cpu":           "cpu",
    "truck":         "truck",
    "filter":        "filter",
    "link":          "link",
    "expand":        "expand",
    "lock":          "lock",
    "edit":          "edit_3",
    "compass":       "compass",
    "crosshair":     "crosshair",
    "activity":      "activity",
}

# Stable ordered list for LLM prompts.
ICON_NAMES: List[str] = sorted(ICON_MAP.keys())


def get_icon_path(name: str) -> Optional[Path]:
    """Resolve a canonical icon name to its on-disk PNG path, or None."""
    fname = ICON_MAP.get(name)
    if fname is None:
        return None
    p = _ICONS_DIR / f"{fname}.png"
    return p if p.exists() else None


def _hex_to_rgb(hex_str: str) -> tuple:
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def resolve_icon(name: Optional[str], color_hex: str = "#1E2761") -> Optional[bytes]:
    """Return PNG bytes for ``name`` recolored to ``color_hex``, or None.

    The bundled icons are pure-black silhouettes on transparent alpha. We tint
    every opaque pixel to the requested accent color, preserving alpha. This
    lets one icon set serve any theme (navy gold, teal, dark-mode light, etc.)
    without shipping per-theme variants.
    """
    if not name:
        return None
    path = get_icon_path(name)
    if path is None:
        logger.debug("Icon %r not found in library; skipping.", name)
        return None
    try:
        img = Image.open(path).convert("RGBA")
    except Exception as e:  # corrupt file etc.
        logger.warning("Failed to open icon %s: %s", path, e)
        return None

    target_rgb = _hex_to_rgb(color_hex)
    # Recolor: keep alpha, replace RGB with target.
    r, g, b, a = img.split()
    colored = Image.merge("RGBA", (
        Image.new("L", img.size, target_rgb[0]),
        Image.new("L", img.size, target_rgb[1]),
        Image.new("L", img.size, target_rgb[2]),
        a,
    ))
    buf = io.BytesIO()
    colored.save(buf, format="PNG")
    return buf.getvalue()


def icon_enum_for_prompt() -> str:
    """Human-readable enum string for injection into LLM prompts."""
    return ", ".join(ICON_NAMES)
