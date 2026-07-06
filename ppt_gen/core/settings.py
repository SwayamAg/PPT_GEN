import os
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
    host: str = "http://localhost:11434"
    model: str = "gemma2"
    default_temperature: float = 0.3
    plan_temperature: float = 0.5
    max_retries: int = 2

class TypographySettings(BaseModel):
    header_font: str = "Arial"
    body_font: str = "Arial"
    font_path: str = "C:/Windows/Fonts/arial.ttf"
    bold_font_path: str = "C:/Windows/Fonts/arialbd.ttf"
    italic_font_path: str = "C:/Windows/Fonts/ariali.ttf"

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

class Settings(BaseModel):
    presentation: PresentationSettings = Field(default_factory=PresentationSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    typography: TypographySettings = Field(default_factory=TypographySettings)
    theme: Optional[ThemeSettings] = None

def load_settings(theme_name: Literal["light", "dark"] = "light") -> Settings:
    """Load config.toml and theme file, merge them into a Settings model."""
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
        
    return Settings(
        presentation=PresentationSettings(**config_data.get("presentation", {})),
        llm=LLMSettings(**config_data.get("llm", {})),
        typography=TypographySettings(**config_data.get("typography", {})),
        theme=ThemeSettings(**theme_data)
    )
