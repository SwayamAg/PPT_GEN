import logging
import os
import re
import zipfile
import io
import requests
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import ImageFont

logger = logging.getLogger("typography")

# Track which font paths we've already warned about so we don't spam the log.
_warned_paths: set = set()

# Constants
DPI = 96.0  # Assumed screen DPI for measuring inches to pixels

# Google Fonts cache directory
FONTS_CACHE_DIR = Path(__file__).resolve().parent / "fonts_cache"
FONTS_CACHE_DIR.mkdir(exist_ok=True)


def download_google_font(font_family: str, weight_style: str = "Regular") -> Optional[str]:
    """
    Download a font from Google Fonts and cache it locally.
    
    Args:
        font_family: The font family name (e.g., "Montserrat", "Inter", "Playfair Display")
        weight_style: The weight/style variant (e.g., "Regular", "Bold", "Italic", "BoldItalic")
    
    Returns:
        Path to the cached TTF/OTF font file, or None if download fails
    """
    # Normalize font family name for URL (replace spaces with +)
    font_url_name = font_family.replace(" ", "+")
    
    # Build cache directory path
    cache_dir = FONTS_CACHE_DIR / font_family.replace(" ", "_")
    cache_dir.mkdir(exist_ok=True)
    
    # Expected cache file path
    cache_file = cache_dir / f"{font_family.replace(' ', '_')}_{weight_style}.ttf"
    
    # Return cached font if already exists
    if cache_file.exists():
        logger.info(f"Using cached Google Font: {cache_file}")
        return str(cache_file)
    
    # Map weight_style to Google Fonts weight values
    weight_map = {
        "Regular": "400",
        "Bold": "700",
        "Italic": "400",
        "BoldItalic": "700",
    }
    weight = weight_map.get(weight_style, "400")
    style = "italic" if "Italic" in weight_style else "normal"
    
    # Google Fonts CSS API URL to get font file URLs
    css_url = f"https://fonts.googleapis.com/css2?family={font_url_name}:wght@{weight}&display=swap"
    
    try:
        logger.info(f"Fetching Google Font CSS for: {font_family} ({weight_style}) from {css_url}")
        response = requests.get(css_url, timeout=30)
        response.raise_for_status()
        
        # Parse the CSS to extract the font file URL
        # Pattern: url(https://fonts.gstatic.com/.../font.ttf) format('truetype')
        url_pattern = r'url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)'
        matches = re.findall(url_pattern, response.text)
        
        if not matches:
            logger.warning(f"No font URLs found in Google Fonts CSS for '{font_family}'")
            return None
        
        # Filter for the correct style (italic/normal)
        font_url = None
        for url in matches:
            if style == "italic" and "italic" in url.lower():
                font_url = url
                break
            elif style == "normal" and "italic" not in url.lower():
                font_url = url
                break
        
        # Fallback to first match if specific style not found
        if not font_url:
            font_url = matches[0]
        
        logger.info(f"Downloading font file from: {font_url}")
        font_response = requests.get(font_url, timeout=30)
        font_response.raise_for_status()
        
        # Save the font file
        with open(cache_file, 'wb') as f:
            f.write(font_response.content)
        
        logger.info(f"Successfully downloaded and cached: {cache_file}")
        return str(cache_file)
        
    except requests.RequestException as e:
        logger.warning(f"Failed to download Google Font '{font_family}': {e}")
    except Exception as e:
        logger.warning(f"Unexpected error downloading font '{font_family}': {e}")
    
    # Clean up empty cache directory on failure
    try:
        if cache_dir.exists() and not any(cache_dir.iterdir()):
            cache_dir.rmdir()
    except Exception:
        pass
    
    return None


def _find_font_in_cache(font_family: str, bold: bool = False, italic: bool = False) -> Optional[str]:
    """Check if a font is already cached locally."""
    weight_style = "Regular"
    if bold and italic:
        weight_style = "BoldItalic"
    elif bold:
        weight_style = "Bold"
    elif italic:
        weight_style = "Italic"
    
    cache_dir = FONTS_CACHE_DIR / font_family.replace(" ", "_")
    if not cache_dir.exists():
        return None
    
    # Look for exact match
    expected_name = f"{font_family.replace(' ', '_')}_{weight_style}.ttf"
    expected_path = cache_dir / expected_name
    if expected_path.exists():
        return str(expected_path)
    
    # Look for any matching variant
    for font_file in cache_dir.glob("*.ttf"):
        if weight_style.lower() in font_file.stem.lower():
            return str(font_file)
    
    # Fallback to any TTF in the font's cache directory
    for font_file in cache_dir.glob("*.ttf"):
        return str(font_file)
    
    return None


def _download_and_cache_font(font_family: str, bold: bool = False, italic: bool = False) -> Optional[str]:
    """Download a Google Font if not in cache."""
    weight_style = "Regular"
    if bold and italic:
        weight_style = "BoldItalic"
    elif bold:
        weight_style = "Bold"
    elif italic:
        weight_style = "Italic"
    
    # Check cache first
    cached = _find_font_in_cache(font_family, bold, italic)
    if cached:
        return cached
    
    # Try to download
    return download_google_font(font_family, weight_style)

def inches_to_pixels(inches: float) -> float:
    return inches * DPI

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width_px: float) -> List[str]:
    """Wrap text into lines using actual pixel measurement of words."""
    paragraphs = text.split("\n")
    all_lines = []
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            all_lines.append("")
            continue
            
        words = paragraph.split(" ")
        current_line = []
        
        for word in words:
            if not word:
                continue
            test_line = " ".join(current_line + [word])
            # Measure width
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0] if bbox else 0
            
            if width <= max_width_px:
                current_line.append(word)
            else:
                if current_line:
                    all_lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # Single word is wider than box width, force split or place it alone
                    all_lines.append(word)
                    current_line = []
                    
        if current_line:
            all_lines.append(" ".join(current_line))
            
    return all_lines

def get_text_height(lines: List[str], font: ImageFont.FreeTypeFont, line_spacing: float = 1.25, num_paragraphs: int = 1) -> float:
    """Calculate the total height in pixels for a block of text lines, including paragraph spacing."""
    if not lines:
        return 0.0
    # Measure line height of standard uppercase/lowercase combination
    bbox = font.getbbox("Hg")
    line_height = (bbox[3] - bbox[1]) if bbox else 16
    text_height = len(lines) * line_height * line_spacing

    # Add paragraph spacing (space_after) for paragraph breaks
    if num_paragraphs > 1:
        font_size_pt = font.size
        space_after_pt = font_size_pt * 0.4 if font_size_pt < 14 else font_size_pt * 0.6
        spacing_px = space_after_pt * (96.0 / 72.0)
        text_height += (num_paragraphs - 1) * spacing_px

    return text_height

def find_optimal_font_size(
    text: str,
    max_width_inches: float,
    max_height_inches: float,
    font_path: str,
    start_size: int = 16,
    min_size: int = 9,
    line_spacing: float = 1.25,
    header_font_path: str = None
) -> Tuple[int, List[str]]:
    """Binary-search down the font size until the wrapped text fits inside the bounding box.

    If it doesn't fit at the minimum font size, truncates lines that exceed the height.

    When ``header_font_path`` is provided and exists, it is used for measurement
    instead of ``font_path``. This lets a theme pair a serif heading font
    (e.g. Cambria) with a sans body font (e.g. Calibri) and have each measured
    with its own metrics — otherwise serif titles sized by sans metrics mis-fit.
    """
    measure_font_path = font_path
    if header_font_path and Path(header_font_path).exists():
        measure_font_path = header_font_path

    max_width_px = inches_to_pixels(max_width_inches)
    max_height_px = inches_to_pixels(max_height_inches)

    # Check if font file exists, fallback to default PIL font if not
    if not Path(measure_font_path).exists():
        if measure_font_path not in _warned_paths:
            logger.warning(f"Font file {measure_font_path} not found. Sizing will use standard Arial fallback.")
            _warned_paths.add(measure_font_path)
        # Try to load Windows default Arial or standard path
        try:
            font_size_px = int(start_size * (96.0 / 72.0))
            font = ImageFont.truetype("arial.ttf", font_size_px)
        except IOError:
            font = ImageFont.load_default()
            return 10, [text]
    
    # Count non-empty paragraphs
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    num_paragraphs = len(paragraphs)

    optimal_size = start_size
    fitting_lines = []
    
    # Binary search down from start_size to min_size
    for size in range(start_size, min_size - 1, -1):
        font_size_px = int(size * (96.0 / 72.0))
        try:
            font = ImageFont.truetype(measure_font_path, font_size_px)
        except IOError:
            font = ImageFont.load_default()
            return 10, [text]

        # Sync line spacing with rendering rules: 1.05 if size < 12, else 1.25 (line_spacing)
        cur_spacing = 1.05 if size < 12 else line_spacing
        lines = wrap_text(text, font, max_width_px)
        height = get_text_height(lines, font, cur_spacing, num_paragraphs)

        if height <= max_height_px:
            optimal_size = size
            fitting_lines = lines
            break
    else:
        # If it doesn't fit even at min_size, we use min_size and truncate lines
        optimal_size = min_size
        font_size_px = int(min_size * (96.0 / 72.0))
        try:
            font = ImageFont.truetype(measure_font_path, font_size_px)
        except IOError:
            font = ImageFont.load_default()
            return 10, [text]
            
        cur_spacing = 1.05
        all_lines = wrap_text(text, font, max_width_px)
        
        # Keep adding lines until we overflow, then append ellipsis
        fitting_lines = []
        current_height = 0.0
        bbox = font.getbbox("Hg")
        line_height = (bbox[3] - bbox[1]) if bbox else 16
        
        for idx, line in enumerate(all_lines):
            test_height = current_height + (line_height * cur_spacing)
            if test_height <= max_height_px:
                fitting_lines.append(line)
                current_height = test_height
            else:
                # Add ellipsis to the last line that fits
                if fitting_lines:
                    fitting_lines[-1] = truncate_text_with_ellipsis(fitting_lines[-1] + "...", font, max_width_px)
                break
                
    return optimal_size, fitting_lines

def truncate_text_with_ellipsis(text: str, font: ImageFont.FreeTypeFont, max_width_px: float) -> str:
    """Helper to truncate a single line and add an ellipsis so it doesn't exceed width."""
    bbox = font.getbbox(text)
    width = bbox[2] - bbox[0] if bbox else 0
    if width <= max_width_px:
        return text
        
    for i in range(len(text), 0, -1):
        test_str = text[:i] + "..."
        b = font.getbbox(test_str)
        w = b[2] - b[0] if b else 0
        if w <= max_width_px:
            return test_str
            
    return "..."
