import logging
from pathlib import Path
from typing import List, Tuple
from PIL import ImageFont

logger = logging.getLogger("typography")

# Constants
DPI = 96.0  # Assumed screen DPI for measuring inches to pixels

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

def get_text_height(lines: List[str], font: ImageFont.FreeTypeFont, line_spacing: float = 1.25) -> float:
    """Calculate the total height in pixels for a block of text lines."""
    if not lines:
        return 0.0
    # Measure line height of standard uppercase/lowercase combination
    bbox = font.getbbox("Hg")
    line_height = (bbox[3] - bbox[1]) if bbox else 16
    return len(lines) * line_height * line_spacing

def find_optimal_font_size(
    text: str,
    max_width_inches: float,
    max_height_inches: float,
    font_path: str,
    start_size: int = 16,
    min_size: int = 9,
    line_spacing: float = 1.25
) -> Tuple[int, List[str]]:
    """Binary-search down the font size until the wrapped text fits inside the bounding box.
    
    If it doesn't fit at the minimum font size, truncates lines that exceed the height.
    """
    max_width_px = inches_to_pixels(max_width_inches)
    max_height_px = inches_to_pixels(max_height_inches)
    
    # Check if font file exists, fallback to default PIL font if not
    if not Path(font_path).exists():
        logger.warning(f"Font file {font_path} not found. Sizing will use standard Arial fallback.")
        # Try a basic system-independent font loader or default font
        try:
            # Try to load Windows default Arial or standard path
            font = ImageFont.truetype("arial.ttf", start_size)
        except IOError:
            font = ImageFont.load_default()
            # Default PIL font doesn't support truetype sizing; return default size
            return 10, [text]
    
    optimal_size = start_size
    fitting_lines = []
    
    # Binary search down from start_size to min_size
    for size in range(start_size, min_size - 1, -1):
        try:
            font = ImageFont.truetype(font_path, size)
        except IOError:
            font = ImageFont.load_default()
            return 10, [text]
            
        lines = wrap_text(text, font, max_width_px)
        height = get_text_height(lines, font, line_spacing)
        
        if height <= max_height_px:
            optimal_size = size
            fitting_lines = lines
            break
    else:
        # If it doesn't fit even at min_size, we use min_size and truncate lines
        optimal_size = min_size
        try:
            font = ImageFont.truetype(font_path, min_size)
        except IOError:
            font = ImageFont.load_default()
            return 10, [text]
            
        all_lines = wrap_text(text, font, max_width_px)
        
        # Keep adding lines until we overflow, then append ellipsis
        fitting_lines = []
        current_height = 0.0
        bbox = font.getbbox("Hg")
        line_height = (bbox[3] - bbox[1]) if bbox else 16
        
        for idx, line in enumerate(all_lines):
            test_height = current_height + (line_height * line_spacing)
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
