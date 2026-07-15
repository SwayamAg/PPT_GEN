from typing import List, Tuple
from ppt_gen.core.settings import Settings
from ppt_gen.core.typography import find_optimal_font_size

def audit_text_fit(
    text: str,
    width_inches: float,
    height_inches: float,
    settings: Settings,
    is_header: bool = False
) -> Tuple[int, List[str]]:
    """Resolve typography constraints by finding the optimal font size and line wraps."""
    # Use bold/headers font settings if designated
    font_path = settings.typography.font_path

    # When the theme declares a distinct header font (e.g. Cambria serif in the
    # navy theme), measure headings with its metrics so titles fit correctly.
    header_font_path = None
    if is_header:
        header_font_path = settings.typography.header_font_path or None
        start_size = 22
        min_size = 14
    else:
        start_size = 18
        min_size = 9

    return find_optimal_font_size(
        text=text,
        max_width_inches=width_inches,
        max_height_inches=height_inches,
        font_path=font_path,
        start_size=start_size,
        min_size=min_size,
        header_font_path=header_font_path
    )
