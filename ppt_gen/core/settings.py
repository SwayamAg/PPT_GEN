import os
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib

# Import Google Fonts downloader
try:
    from ppt_gen.core.typography import _download_and_cache_font
except ImportError:
    _download_and_cache_font = None

class PresentationSettings(BaseModel):
    width_inches: float = 13.33
    height_inches: float = 7.5
    grid_cols: int = 12
    grid_rows: int = 8
    margin_left: float = 0.5
    margin_right: float = 0.5
    margin_top: float = 0.5
    margin_bottom: float = 0.5
    gutter_width: float = 0.15
    gutter_height: float = 0.15

class LLMSettings(BaseModel):
    provider: str = "ollama"
    host: str = "http://localhost:11434"
    model: str = "gemma2"
    default_temperature: float = 0.3
    plan_temperature: float = 0.5
    max_retries: int = 2
    api_key: Optional[str] = None

def _find_font(candidates: list[str]) -> str:
    """Return the first candidate font path that exists on disk, else the last candidate."""
    for p in candidates:
        if Path(p).exists():
            return p
    return candidates[-1]  # Let the font library warn; don't crash here


# Logical-name → per-OS candidate paths
_FONT_CANDIDATES: dict = {
    # (name_lower, bold, italic) -> [candidates...]
    # Windows stores font files lowercase; some installs have uppercase.
    # Linux: Liberation = metrically-compatible Arial/Calibri replacement.
    #        DejaVu     = universal fallback.
}

_LINUX_SANS = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    # Nix/Nixpacks standard paths
    "/nix/var/nix/profiles/default/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/nix/var/nix/profiles/default/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    os.path.expanduser("~/.nix-profile/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    os.path.expanduser("~/.nix-profile/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    os.path.expanduser("~/.nix-profile/share/fonts/dejavu/DejaVuSans.ttf"),
    os.path.expanduser("~/.nix-profile/share/fonts/liberation/LiberationSans-Regular.ttf"),
    # Generic barenames for PIL's internal resolution via fontconfig
    "LiberationSans-Regular.ttf",
    "DejaVuSans.ttf",
]
_LINUX_SANS_BOLD = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    # Nix/Nixpacks standard paths
    "/nix/var/nix/profiles/default/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/nix/var/nix/profiles/default/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    os.path.expanduser("~/.nix-profile/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    os.path.expanduser("~/.nix-profile/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    os.path.expanduser("~/.nix-profile/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    os.path.expanduser("~/.nix-profile/share/fonts/liberation/LiberationSans-Bold.ttf"),
    # Generic barenames
    "LiberationSans-Bold.ttf",
    "DejaVuSans-Bold.ttf",
]
_LINUX_SANS_ITALIC = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    # Nix/Nixpacks standard paths
    "/nix/var/nix/profiles/default/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
    "/nix/var/nix/profiles/default/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    os.path.expanduser("~/.nix-profile/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"),
    os.path.expanduser("~/.nix-profile/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
    os.path.expanduser("~/.nix-profile/share/fonts/dejavu/DejaVuSans-Oblique.ttf"),
    os.path.expanduser("~/.nix-profile/share/fonts/liberation/LiberationSans-Italic.ttf"),
    # Generic barenames
    "LiberationSans-Italic.ttf",
    "DejaVuSans-Oblique.ttf",
]


def _platform_font(name: str, bold: bool = False, italic: bool = False) -> str:
    """Resolve a best-guess system font path for the given logical font name.
    
    Falls back to downloading from Google Fonts if the font is not installed locally.
    """
    is_mac   = sys.platform == "darwin"
    is_linux = sys.platform.startswith("linux")

    base = name.lower().replace(" ", "")

    if is_mac:
        mac_dirs = [
            "/Library/Fonts",
            "/System/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
        ]
        suffix = "Bold" if bold else ("Italic" if italic else "")
        variants = [
            f"{name}{suffix}.ttf",
            f"{name}{suffix}.otf",
            f"{base}{suffix.lower()}.ttf",
        ]
        candidates = [f"{d}/{v}" for d in mac_dirs for v in variants]
        candidates += [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Arial.ttf",
        ]
        found = _find_font(candidates)
        if Path(found).exists():
            return found
        # Fallback to Google Fonts
        return _try_google_fonts(name, bold, italic) or found

    if is_linux:
        if bold:
            found = _find_font(_LINUX_SANS_BOLD)
        elif italic:
            found = _find_font(_LINUX_SANS_ITALIC)
        else:
            found = _find_font(_LINUX_SANS)
        if Path(found).exists():
            return found
        # Fallback to Google Fonts
        return _try_google_fonts(name, bold, italic) or found

    # Windows — build candidates with both lowercase and uppercase filename variants
    win_dir = "C:/Windows/Fonts"
    suffix_map = {
        # (bold, italic) -> common filename suffixes per font family
        "arial":   {(False,False):"arial",    (True,False):"arialbd",   (False,True):"ariali",  (True,True):"arialbi"},
        "calibri": {(False,False):"calibri",  (True,False):"calibrib",  (False,True):"calibrii",(True,True):"calibriz"},
        "cambria": {(False,False):"cambria",  (True,False):"cambriab",  (False,True):"cambriai",(True,True):"cambriaz"},
        "calibril":{(False,False):"calibril", (True,False):"calibril",  (False,True):"calibril",(True,True):"calibril"},
    }
    key = (bold, italic)
    if base in suffix_map:
        stem = suffix_map[base][key]
        candidates = [
            f"{win_dir}/{stem}.ttf",
            f"{win_dir}/{stem.upper()}.TTF",
            f"{win_dir}/{stem}.ttc",   # cambria ships as .ttc
        ]
        # cambria special case
        if base == "cambria" and not bold and not italic:
            candidates.insert(0, f"{win_dir}/cambria.ttc")
        found = _find_font(candidates)
        if Path(found).exists():
            return found
        # Fallback to Google Fonts
        return _try_google_fonts(name, bold, italic) or found

    # Generic fallback for unknown font names
    # First check if the requested font exists in Windows Fonts
    suffix = "bd" if bold else ("i" if italic else "")
    font_candidates = [
        f"{win_dir}/{base}{suffix}.ttf",
        f"{win_dir}/{base}{suffix}.ttc",
    ]
    found = _find_font(font_candidates)
    if Path(found).exists():
        return found
    # Font not found locally — try Google Fonts
    google_font = _try_google_fonts(name, bold, italic)
    if google_font:
        return google_font
    # Google Fonts failed — fall back to Arial
    return _find_font([f"{win_dir}/arial.ttf"])


def _try_google_fonts(name: str, bold: bool, italic: bool) -> Optional[str]:
    """Try to download and cache a font from Google Fonts."""
    if _download_and_cache_font is None:
        return None
    # Skip downloading standard fonts that are proprietary or not hosted on Google Fonts
    standard_fonts = {
        "arial", "calibri", "cambria", "timesnewroman", "times", "helvetica", 
        "georgia", "courier", "couriernew", "verdana", "trebuchetms", 
        "garamond", "bookman", "dejavusans", "liberationsans", "dejavusans-bold",
        "dejavusans-oblique", "liberationsans-regular", "liberationsans-bold",
        "liberationsans-italic"
    }
    if name.lower().replace(" ", "").replace("-", "") in standard_fonts:
        return None
    try:
        return _download_and_cache_font(name, bold, italic)
    except Exception as e:
        import logging
        logging.getLogger("settings").warning(f"Google Fonts download failed for '{name}': {e}")
        return None


class TypographySettings(BaseModel):
    header_font: str = "Arial"
    body_font: str = "Arial"
    font_path: str = Field(default_factory=lambda: _platform_font("Arial"))
    bold_font_path: str = Field(default_factory=lambda: _platform_font("Arial", bold=True))
    italic_font_path: str = Field(default_factory=lambda: _platform_font("Arial", italic=True))
    # Serif (or distinct) font files used to measure headings. When None, the
    # body font files above are used. Lets a theme pair serif headings with
    # sans body text (e.g. Cambria + Calibri in the navy theme).
    header_font_path: Optional[str] = None
    header_bold_font_path: Optional[str] = None

class ThemeSettings(BaseModel):
    background: str
    text_primary: str
    text_secondary: str
    accent_primary: str
    accent_secondary: str
    accent_tertiary: str
    accent_quaternary: str
    card_bg: str
    card_border: str
    chart_colors: List[str]
    # Phase A — optional extended tokens (defaults keep light/dark themes working).
    # Background used by "title"/"closing" archetypes (e.g. navy cover slide).
    title_slide_background: Optional[str] = None
    # Fill color for filled insight-callout boxes.
    insight_box_bg: Optional[str] = None
    # Color for small uppercase letter-spaced eyebrow labels.
    eyebrow_color: Optional[str] = None
    # Muted footer line color on title/closing slides.
    footer_color: Optional[str] = None

class ChartSettings(BaseModel):
    # When True, charts render as native editable PPTX chart objects where the
    # chart_engine_native supports the type; otherwise Matplotlib PNGs are used.
    # Waterfall and heatmap are never native (no PPTX primitive) — they always
    # fall back to Matplotlib regardless of this flag.
    native: bool = True

class Settings(BaseModel):
    presentation: PresentationSettings = Field(default_factory=PresentationSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    typography: TypographySettings = Field(default_factory=TypographySettings)
    charts: ChartSettings = Field(default_factory=ChartSettings)
    theme: Optional[ThemeSettings] = None

def _resolve_font_paths(typo_data: dict) -> dict:
    """Replace hardcoded Windows font paths with runtime-resolved platform paths.

    If a theme TOML supplies '*_font_path' as a raw Windows path that doesn't
    exist on the current OS, we fall back to resolving it from the logical
    font name keys (header_font / body_font) via _platform_font().

    If the theme specifies a different font name than the config default,
    we prioritize resolving that font name (via system fonts or Google Fonts)
    over the config's hardcoded path.
    """
    body_name  = typo_data.get("body_font",   "Arial")
    header_name = typo_data.get("header_font", body_name)

    # Check if theme explicitly specifies a different font than config default
    # (config.toml defaults to Arial). If so, we should try to resolve the
    # theme's font name first, rather than using config's hardcoded Arial path.
    config_default_body = "Arial"
    config_default_header = "Arial"
    
    body_name_differs = body_name.lower() != config_default_body.lower()
    header_name_differs = header_name.lower() != config_default_header.lower()

    def _resolve(key: str, name: str, bold: bool = False, italic: bool = False, name_differs: bool = False):
        raw = typo_data.get(key)
        # If theme specifies a different font name, don't use config's hardcoded path
        if raw and Path(raw).exists() and not name_differs:
            return raw  # path works as-is on this platform
        return _platform_font(name, bold=bold, italic=italic)

    out = dict(typo_data)
    out["font_path"]         = _resolve("font_path",         body_name, name_differs=body_name_differs)
    out["bold_font_path"]    = _resolve("bold_font_path",    body_name,   bold=True, name_differs=body_name_differs)
    out["italic_font_path"]  = _resolve("italic_font_path",  body_name,   italic=True, name_differs=body_name_differs)
    if "header_font_path" in typo_data or header_name != body_name:
        out["header_font_path"]      = _resolve("header_font_path",      header_name, name_differs=header_name_differs)
        out["header_bold_font_path"] = _resolve("header_bold_font_path", header_name, bold=True, name_differs=header_name_differs)
    return out


def load_settings(theme_name: str = "light") -> Settings:
    """Load config.toml and theme file, merge them into a Settings model.

    A theme TOML may optionally carry a ``[fonts]`` block (header_font,
    body_font, *_font_path) and a ``[charts]`` block (native) — these take
    precedence over the same keys in config.toml. This lets a theme like
    ``navy`` pair Cambria headings with Calibri body text while ``light``
    keeps the existing Arial defaults.
    """
    core_dir = Path(__file__).resolve().parent
    root_dir = core_dir.parent

    config_path = root_dir / "config" / "config.toml"
    theme_path = root_dir / "themes" / f"{theme_name}.toml"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    if not theme_path.exists():
        raise FileNotFoundError(f"Theme file not found: {theme_path}")

    with open(config_path, "rb") as f:
        config_data = tomllib.load(f)

    with open(theme_path, "rb") as f:
        theme_data = tomllib.load(f)

    # config.toml supplies the base typography/charts; theme overrides win.
    typo_data = dict(config_data.get("typography", {}))
    typo_data.update(theme_data.get("fonts", {}))
    # Resolve *_font_path values cross-platform (Windows paths fail on Linux)
    typo_data = _resolve_font_paths(typo_data)

    charts_data = dict(config_data.get("charts", {}))
    charts_data.update(theme_data.get("charts", {}))

    return Settings(
        presentation=PresentationSettings(**config_data.get("presentation", {})),
        llm=LLMSettings(**config_data.get("llm", {})),
        typography=TypographySettings(**typo_data),
        charts=ChartSettings(**charts_data),
        theme=ThemeSettings(**{k: v for k, v in theme_data.items() if k not in ("fonts", "charts")})
    )
