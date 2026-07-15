import os
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib

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


def _platform_font(name: str, bold: bool = False, italic: bool = False) -> str:
    """Resolve a best-guess system font path for the given logical font name."""
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
        # Reliable macOS fallbacks
        candidates += [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Arial.ttf",
        ]
        return _find_font(candidates)

    if is_linux:
        fc = {"bold": "Bold", "italic": "Italic", "": ""}[
            "bold" if bold else ("italic" if italic else "")
        ]
        return _find_font([
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-' + fc if fc else ''}.ttf",
            f"/usr/share/fonts/truetype/liberation/LiberationSans{'-' + fc if fc else ''}-Regular.ttf",
        ])

    # Windows fallback
    suffix = "bd" if bold else ("i" if italic else "")
    return f"C:/Windows/Fonts/{base}{suffix}.ttf"


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

def load_settings(theme_name: Literal["light", "dark", "navy"] = "light") -> Settings:
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

    charts_data = dict(config_data.get("charts", {}))
    charts_data.update(theme_data.get("charts", {}))

    return Settings(
        presentation=PresentationSettings(**config_data.get("presentation", {})),
        llm=LLMSettings(**config_data.get("llm", {})),
        typography=TypographySettings(**typo_data),
        charts=ChartSettings(**charts_data),
        theme=ThemeSettings(**{k: v for k, v in theme_data.items() if k not in ("fonts", "charts")})
    )
