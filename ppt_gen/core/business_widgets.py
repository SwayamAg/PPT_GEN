"""
business_widgets.py — §6 Tier A widget renderers.

Each render function takes a python-pptx slide object + position/size in
Inches + payload dict + theme and draws directly using python-pptx shapes.
No Matplotlib, no chart library — pure shape arithmetic.

Render functions (one per Tier A widget):
  render_kpi_card            — bordered card with big value + label + optional trend arrow
  render_progress_indicator  — background track + filled portion + % label
  render_growth_arrow        — chevron arrow shape + value + vs-prior caption
  render_benchmark_bar       — filled bar + target-line marker + two labels
  render_market_share_strip  — proportional N-segment horizontal strip
  render_scorecard           — compact grid of sub-metrics (dot + label + value rows)
  render_matrix_view         — BCG-style quadrant with dots at (x, y) positions
  render_variance_graphic    — horizontal bars extending left/right from a centre line
"""

import logging
import io
import tempfile
from typing import Any, Dict, List, Optional

from PIL import Image
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_AUTO_SIZE, MSO_ANCHOR

from ppt_gen.core.settings import ThemeSettings

logger = logging.getLogger("business_widgets")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(*(int(h[i : i + 2], 16) for i in (0, 2, 4)))


def _add_rect(slide, left, top, width, height, fill_hex: str, line_hex: Optional[str] = None, line_pt: float = 0.5):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = _hex_to_rgb(fill_hex)
    if line_hex:
        shape.line.color.rgb = _hex_to_rgb(line_hex)
        shape.line.width = Pt(line_pt)
    else:
        shape.line.fill.background()
    return shape


def _add_textbox(slide, left, top, width, height, text: str, font_size: int,
                 color_hex: str, bold: bool = False, italic: bool = False,
                 font_name: str = "Calibri", auto_fit: bool = True, valign=None):
    tx = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tx.text_frame
    tf.word_wrap = True
    if auto_fit:
        tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    if valign is not None:
        tf.vertical_anchor = valign
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.02)
    p = tf.paragraphs[0]
    p.text = text
    p.font.name = font_name
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.italic = italic
    p.font.color.rgb = _hex_to_rgb(color_hex)
    return tx


def render_kpi_card(
    slide, payload: Dict[str, Any], theme: ThemeSettings,
    left: float, top: float, width: float, height: float,
    header_font: str = "Calibri", body_font: str = "Calibri",
    dark_mode: bool = False
):
    """Phase D restyle: vertical KPI card with optional icon.

    Layout (top → bottom):
      • icon region (~25% of height) — when payload includes an 'icon' key
        matching a name in ICON_MAP, the icon is recolored to accent_primary
        and centered in this band.
      • value (large, serif/header_font) — the headline metric
      • label (small, sans/body_font) — caption describing the metric

    The accent-bar-left look is replaced with a clean top-down stack matching
    the reference deck's hero KPI pattern.
    """
    value = str(payload.get("value", "") or "—")
    label = str(payload.get("label", ""))
    icon_name = payload.get("icon")  # optional: e.g. "trend_up", "rupee", "target"

    # Phase H: dark-mode color overrides
    if dark_mode:
        val_color = "#FFFFFF"
        lbl_color = "#FFFFFFAA"
        icon_color = "#FFFFFF"
    else:
        val_color = theme.accent_primary
        lbl_color = theme.text_secondary
        icon_color = theme.accent_primary

    # Icon region — reserved top band. If an icon is specified, draw it here.
    icon_region_h = min(0.35, height * 0.22)
    if icon_name:
        from ppt_gen.core.icon_library import resolve_icon
        icon_bytes = resolve_icon(icon_name, icon_color)
        if icon_bytes:
            icon_img = Image.open(io.BytesIO(icon_bytes))
            # Center horizontally in the icon region
            icon_w = 0.30
            icon_h = 0.30
            icon_left = left + (width - icon_w) / 2
            icon_top = top + (icon_region_h - icon_h) / 2
            # Save to temp and add as picture
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                icon_img.save(tmp.name)
                slide.shapes.add_picture(tmp.name, Inches(icon_left), Inches(icon_top),
                                         Inches(icon_w), Inches(icon_h))

    # Proportional font scaling based on widget height to prevent leakage
    lbl_fs = max(9, min(14, int(height * 8.5)))
    val_fs = max(16, min(32, int(height * 20.0)))

    # Value — large, serif (header_font), centered below icon region
    val_top = top + icon_region_h + height * 0.04
    val_h = height * 0.42
    _add_textbox(
        slide, left + 0.06, val_top,
        width - 0.12, val_h,
        value, font_size=val_fs, color_hex=val_color, bold=True,
        font_name=header_font
    )

    # Label — small caption below, sans (body_font)
    lbl_top = val_top + val_h + height * 0.02
    _add_textbox(
        slide, left + 0.06, lbl_top,
        width - 0.12, height * 0.30,
        label, font_size=lbl_fs, color_hex=lbl_color,
        font_name=body_font
    )


# ---------------------------------------------------------------------------
# 2. progress_indicator — track rectangle + filled portion + % label
# ---------------------------------------------------------------------------

def render_progress_indicator(
    slide, payload: Dict[str, Any], theme: ThemeSettings,
    left: float, top: float, width: float, height: float,
    header_font: str = "Calibri", body_font: str = "Calibri"
):
    """Background track + filled portion rectangle + % label.
    Label in body_font; percentage value in header_font."""
    value_str = str(payload.get("value", "") or "")
    label = str(payload.get("label", ""))

    # Parse numeric value (strip arrows/% etc.)
    import re
    nums = re.findall(r"\d+", value_str)
    pct = int(nums[0]) if nums else 50
    pct = max(0, min(100, pct))

    track_h = 0.18
    track_top = top + height * 0.4
    track_margin = 0.1

    # Track background
    _add_rect(slide, left + track_margin, track_top,
              width - 2 * track_margin, track_h, theme.card_border)

    # Filled portion
    fill_w = max(0.01, (width - 2 * track_margin) * pct / 100)
    _add_rect(slide, left + track_margin, track_top,
              fill_w, track_h, theme.accent_primary)

    # Proportional font scaling to prevent text leakage
    lbl_fs = max(9, min(14, int(height * 8.5)))
    pct_fs = max(10, min(18, int(height * 12.0)))

    # Label above bar (body_font)
    _add_textbox(slide, left + track_margin, top + height * 0.1,
                 width - 2 * track_margin, height * 0.28,
                 label, font_size=lbl_fs, color_hex=theme.text_secondary,
                 font_name=body_font)

    # % value to the right of bar (header_font, bold)
    _add_textbox(
        slide, left + track_margin, track_top + track_h + 0.04,
        width - 2 * track_margin, 0.25,
        f"{pct}%", font_size=pct_fs, color_hex=theme.accent_primary, bold=True,
        font_name=header_font
    )


# ---------------------------------------------------------------------------
# 3. growth_arrow — chevron + value + "vs last period" caption
# ---------------------------------------------------------------------------

def render_growth_arrow(
    slide, payload: Dict[str, Any], theme: ThemeSettings,
    left: float, top: float, width: float, height: float,
    header_font: str = "Calibri", body_font: str = "Calibri"
):
    """Chevron/arrow shape + big number + vs-prior caption.
    Value in header_font; label in body_font."""
    value_str = str(payload.get("value", "") or "")
    label = str(payload.get("label", ""))

    import re
    nums = re.findall(r"\d+", value_str)
    pct = int(nums[0]) if nums else 0

    # Direction
    is_up = "↑" in value_str or ("↓" not in value_str and pct >= 0)
    arrow_color = theme.accent_secondary if is_up else theme.accent_tertiary

    # Proportional font scaling to prevent text leakage
    base_fs = max(9, min(14, int(height * 8.5)))
    val_fs = max(14, min(28, int(height * 18.0)))
    lbl_fs = base_fs

    # Arrow symbol block (header_font for the symbol)
    arrow_char = "▲" if is_up else "▼"
    arrow_top = top + height * 0.08
    _add_textbox(
        slide, left + 0.05, arrow_top, width * 0.25, height * 0.45,
        arrow_char, font_size=val_fs, color_hex=arrow_color, bold=True,
        font_name=header_font
    )

    # Value — big number (header_font)
    _add_textbox(
        slide, left + width * 0.28, arrow_top,
        width * 0.68, height * 0.48,
        value_str, font_size=val_fs, color_hex=theme.accent_primary, bold=True,
        font_name=header_font
    )

    # Label caption (body_font)
    _add_textbox(
        slide, left + 0.05, top + height * 0.57,
        width - 0.1, height * 0.38,
        label, font_size=lbl_fs, color_hex=theme.text_secondary,
        font_name=body_font
    )


# ---------------------------------------------------------------------------
# 4. benchmark_bar — filled bar + thin target-line marker + two labels
# ---------------------------------------------------------------------------

def render_benchmark_bar(
    slide, payload: Dict[str, Any], theme: ThemeSettings,
    left: float, top: float, width: float, height: float,
    header_font: str = "Calibri", body_font: str = "Calibri"
):
    """Horizontal filled bar + vertical target-line marker + current/target labels.

    Label renders in body_font; actual/target values in header_font (bold).
    """
    import re

    def _parse(s: str) -> float:
        nums = re.findall(r"\d+(?:\.\d+)?", str(s))
        return float(nums[0]) if nums else 50.0

    actual_val = _parse(payload.get("value", "") or payload.get("actual_value", 50))
    target_val = _parse(payload.get("target", "") or payload.get("target_value", 70))
    label = str(payload.get("label", ""))

    bar_h = 0.22
    bar_top = top + height * 0.42
    track_margin = 0.1
    track_w = width - 2 * track_margin

    # Scale: max of actual/target is 100% width
    max_val = max(actual_val, target_val, 1)

    # Track
    _add_rect(slide, left + track_margin, bar_top, track_w, bar_h, theme.card_border)

    # Filled actual bar
    actual_w = track_w * (actual_val / max_val)
    _add_rect(slide, left + track_margin, bar_top, max(0.02, actual_w), bar_h, theme.accent_primary)

    # Target marker line (thin vertical line at target position)
    target_x = left + track_margin + track_w * (target_val / max_val)
    marker_h = bar_h + 0.08
    _add_rect(slide, target_x - 0.015, bar_top - 0.04, 0.025, marker_h, theme.accent_tertiary)

    # Proportional font scaling to prevent text leakage
    base_fs = max(9, min(14, int(height * 8.5)))
    lbl_fs = base_fs
    val_fs = base_fs - 1

    # Label (body_font)
    _add_textbox(slide, left + track_margin, top + 0.06,
                 track_w, height * 0.3,
                 label, font_size=lbl_fs, color_hex=theme.text_secondary,
                 font_name=body_font)

    # Actual value label left-aligned below bar (header_font, bold)
    _add_textbox(slide, left + track_margin, bar_top + bar_h + 0.04,
                 track_w * 0.45, 0.22,
                 f"Actual: {actual_val:.0f}", font_size=val_fs, color_hex=theme.text_primary, bold=True,
                 font_name=header_font)

    # Target value label right-aligned below target marker (header_font, bold)
    _add_textbox(slide, left + track_margin + track_w * 0.5, bar_top + bar_h + 0.04,
                 track_w * 0.5, 0.22,
                 f"Target: {target_val:.0f}", font_size=14, color_hex=theme.accent_tertiary, bold=True,
                 font_name=header_font)


# ---------------------------------------------------------------------------
# 5. market_share_strip — proportional N-segment horizontal strip
# ---------------------------------------------------------------------------

STRIP_PALETTE = [
    "#2563EB",  # blue
    "#059669",  # emerald
    "#D97706",  # amber
    "#DC2626",  # red
    "#7C3AED",  # violet
    "#0891B2",  # cyan
]


def render_market_share_strip(
    slide, payload: Dict[str, Any], theme: ThemeSettings,
    left: float, top: float, width: float, height: float,
    header_font: str = "Calibri", body_font: str = "Calibri"
):
    """One 100%-wide bar divided into N adjacent colored segments.

    Overall label renders in body_font; segment labels in body_font.
    """
    data = payload.get("data", {})
    labels = data.get("labels", ["A", "B", "C", "D"]) if data else ["A", "B", "C", "D"]
    series = data.get("series", []) if data else []
    values = series[0]["values"] if series else [25, 25, 25, 25]
    overall_label = str(payload.get("label", ""))

    strip_h = 0.28
    strip_top = top + height * 0.35
    strip_margin = 0.1
    strip_w = width - 2 * strip_margin

    total = sum(values) or 1
    cx = left + strip_margin

    for i, (lbl, val) in enumerate(zip(labels, values)):
        seg_w = strip_w * (val / total)
        color = STRIP_PALETTE[i % len(STRIP_PALETTE)]
        _add_rect(slide, cx, strip_top, max(0.01, seg_w), strip_h, color)
        # Segment label below strip (body_font)
        if seg_w > 0.25:
            _add_textbox(slide, cx, strip_top + strip_h + 0.04, seg_w, 0.2,
                         f"{lbl}\n{val:.0f}%", font_size=12, color_hex=theme.text_secondary,
                         font_name=body_font)
        cx += seg_w

    # Overall label above strip (body_font)
    _add_textbox(slide, left + strip_margin, top + 0.06, strip_w, height * 0.25,
                 overall_label, font_size=16, color_hex=theme.text_secondary,
                 font_name=body_font)


# ---------------------------------------------------------------------------
# 6. scorecard — compact grid of 2–4 sub-metrics: dot + label + value rows
# ---------------------------------------------------------------------------

DOT_COLORS = ["#059669", "#059669", "#D97706", "#DC2626"]


def render_scorecard(
    slide, payload: Dict[str, Any], theme: ThemeSettings,
    left: float, top: float, width: float, height: float,
    header_font: str = "Calibri", body_font: str = "Calibri"
):
    """Compact grid of sub-metric rows: colored dot + label + value.

    Header renders in body_font; labels in body_font, values in header_font (bold).
    """
    data = payload.get("data", {})
    label_text = str(payload.get("label", "Performance Scorecard"))

    # Build sub-metric rows from deviation_from_target data if available
    rows: List[Dict] = []
    if data and isinstance(data, dict):
        for i, (lbl, actual, target) in enumerate(zip(
            data.get("labels", []),
            data.get("series", [{}])[0].get("values", []) if data.get("series") else [],
            data.get("series", [{}, {}])[1].get("values", []) if len(data.get("series", [])) > 1 else []
        )):
            gap = actual - target
            rows.append({"label": lbl, "actual": actual, "target": target, "gap": gap, "idx": i})

    if not rows:
        # Default rows if no data
        rows = [
            {"label": "Revenue", "actual": 72, "target": 70, "gap": 2, "idx": 0},
            {"label": "Margin", "actual": 45, "target": 50, "gap": -5, "idx": 1},
            {"label": "Volume", "actual": 88, "target": 80, "gap": 8, "idx": 2},
            {"label": "NPS", "actual": 63, "target": 65, "gap": -2, "idx": 3},
        ]

    # Header (body_font)
    _add_textbox(slide, left + 0.08, top + 0.06, width - 0.16, 0.25,
                 label_text, font_size=16, color_hex=theme.text_secondary, bold=True,
                 font_name=body_font)

    row_h = min(0.35, (height - 0.35) / max(len(rows), 1))

    for i, row in enumerate(rows[:4]):
        ry = top + 0.35 + i * row_h
        gap = row.get("gap", 0)
        dot_color = "#059669" if gap >= 0 else "#DC2626"

        # Dot indicator
        dot_shape = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(left + 0.1), Inches(ry + row_h * 0.3),
            Inches(0.12), Inches(0.12)
        )
        dot_shape.fill.solid()
        dot_shape.fill.fore_color.rgb = _hex_to_rgb(dot_color)
        dot_shape.line.fill.background()

        # Label (body_font)
        _add_textbox(slide, left + 0.28, ry + row_h * 0.15,
                     width * 0.5, row_h * 0.7,
                     str(row.get("label", "")), font_size=16, color_hex=theme.text_primary,
                     font_name=body_font)

        # Value (header_font, bold)
        actual = row.get("actual", 0)
        target = row.get("target", 0)
        val_str = f"{actual:.0f} / {target:.0f}"
        _add_textbox(slide, left + width * 0.6, ry + row_h * 0.15,
                     width * 0.35, row_h * 0.7,
                     val_str, font_size=16, color_hex=theme.text_primary, bold=True,
                     font_name=header_font)


# ---------------------------------------------------------------------------
# 7. matrix_view — BCG/prioritization quadrant with dots at (x, y) positions
# ---------------------------------------------------------------------------

def render_matrix_view(
    slide, payload: Dict[str, Any], theme: ThemeSettings,
    left: float, top: float, width: float, height: float,
    header_font: str = "Calibri", body_font: str = "Calibri"
):
    """BCG-style quadrant divided into 4 quadrants with initiative dots.

    Title/header renders in body_font (consistent with other widgets);
    quadrant labels and item labels in body_font.
    """
    data = payload.get("data", {})
    label_text = str(payload.get("label", "Prioritization Matrix"))
    items: List[Dict] = data.get("items", []) if data else []

    if not items:
        items = [
            {"label": "Initiative A", "x": 0.8, "y": 0.8},
            {"label": "Initiative B", "x": 0.3, "y": 0.75},
            {"label": "Initiative C", "x": 0.75, "y": 0.35},
            {"label": "Initiative D", "x": 0.25, "y": 0.3},
        ]

    matrix_margin = 0.15
    matrix_top = top + 0.4
    matrix_w = width - 2 * matrix_margin
    matrix_h = height - 0.5

    # Outer border of matrix
    border = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(left + matrix_margin), Inches(matrix_top),
        Inches(matrix_w), Inches(matrix_h)
    )
    border.fill.background()
    border.line.color.rgb = _hex_to_rgb(theme.card_border)
    border.line.width = Pt(0.5)

    # Vertical divider (centre)
    cx = left + matrix_margin + matrix_w / 2
    _add_rect(slide, cx - 0.01, matrix_top, 0.02, matrix_h, theme.card_border)

    # Horizontal divider (centre)
    my = matrix_top + matrix_h / 2
    _add_rect(slide, left + matrix_margin, my - 0.01, matrix_w, 0.02, theme.card_border)

    # Quadrant labels
    quad_labels = [("High Impact\nLow Effort", 0, 0),   # top-left
                   ("High Impact\nHigh Effort", 1, 0),  # top-right
                   ("Low Impact\nLow Effort", 0, 1),    # bottom-left
                   ("Low Impact\nHigh Effort", 1, 1)]   # bottom-right
    qw = matrix_w / 2
    qh = matrix_h / 2

    for qlbl, qcol, qrow in quad_labels:
        qx = left + matrix_margin + qcol * qw + 0.04
        qy = matrix_top + qrow * qh + 0.04
        # Scale font proportionally to quadrant height to avoid overflow
        q_font = max(7, min(10, int(qh * 7)))
        _add_textbox(slide, qx, qy, qw - 0.08, 0.3,
                     qlbl, font_size=q_font, color_hex=theme.text_secondary, font_name=body_font)

    # Title (body_font)
    _add_textbox(slide, left + matrix_margin, top + 0.06, matrix_w, 0.28,
                 label_text, font_size=16, color_hex=theme.text_secondary, bold=True,
                 font_name=body_font)

    # X/Y axis labels (body_font)
    _add_textbox(slide, left + matrix_margin, matrix_top + matrix_h + 0.04,
                 matrix_w, 0.2,
                 "← Effort →", font_size=12, color_hex=theme.text_secondary, font_name=body_font)

    # Plot items as dots
    ITEM_COLORS = [theme.accent_primary, theme.accent_secondary,
                   theme.accent_tertiary, theme.card_border]

    for i, item in enumerate(items[:6]):
        # x=effort (0=low,1=high), y=impact (0=low,1=high)
        x_frac = float(item.get("x", 0.5))
        y_frac = float(item.get("y", 0.5))
        dot_x = left + matrix_margin + x_frac * matrix_w
        # Invert y: y=1 (high impact) → top of matrix
        dot_y = matrix_top + (1 - y_frac) * matrix_h

        dot_size = 0.15
        dot_shape = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(dot_x - dot_size / 2), Inches(dot_y - dot_size / 2),
            Inches(dot_size), Inches(dot_size)
        )
        color = ITEM_COLORS[i % len(ITEM_COLORS)]
        dot_shape.fill.solid()
        dot_shape.fill.fore_color.rgb = _hex_to_rgb(color)
        dot_shape.line.fill.background()

        # Item label — small proportional font so it doesn't overflow onto other dots
        item_font = max(7, min(10, int(matrix_h * 6)))
        _add_textbox(slide, dot_x + 0.1, dot_y - 0.1, 0.6, 0.2,
                     str(item.get("label", f"Item {i+1}")),
                     font_size=item_font, color_hex=theme.text_primary, font_name=body_font)


# ---------------------------------------------------------------------------
# 8. variance_graphic — horizontal bars extending L/R from centre zero-line
# ---------------------------------------------------------------------------

def render_variance_graphic(
    slide, payload: Dict[str, Any], theme: ThemeSettings,
    left: float, top: float, width: float, height: float,
    header_font: str = "Calibri", body_font: str = "Calibri"
):
    """Horizontal bars extending left/right from a centre zero-line, colored by sign.

    Label renders in body_font; actual/target values in header_font.
    """
    import re

    def _parse(s: Any) -> float:
        nums = re.findall(r"-?\d+(?:\.\d+)?", str(s))
        return float(nums[0]) if nums else 0.0

    actual_val = _parse(payload.get("value", "") or payload.get("actual_value", 50))
    target_val = _parse(payload.get("target", "") or payload.get("target_value", 50))
    label = str(payload.get("label", ""))

    variance = actual_val - target_val
    is_positive = variance >= 0

    bar_h = 0.2
    bar_top = top + height * 0.38
    center_x = left + width / 2
    max_half_w = (width - 0.2) / 2

    # Scale bar width proportionally (cap at max half width)
    max_variance = max(abs(variance), 0.001)
    bar_w = min(max_half_w, max_half_w * abs(variance) / max(abs(variance), 20))
    bar_color = theme.accent_secondary if is_positive else theme.accent_tertiary

    # Centre zero-line
    _add_rect(slide, center_x - 0.01, bar_top - 0.04, 0.02, bar_h + 0.08, theme.card_border)

    # Variance bar
    if is_positive:
        bar_left = center_x
    else:
        bar_left = center_x - bar_w

    _add_rect(slide, bar_left, bar_top, bar_w, bar_h, bar_color)

    # Proportional font scaling based on widget height and width to prevent text overflow/leakage
    base_fs = max(9, min(14, int(height * 8.5)))
    lbl_fs = base_fs
    val_fs = base_fs + 1
    flank_fs = base_fs - 1

    # Label above (body_font)
    _add_textbox(slide, left + 0.06, top + 0.06, width - 0.12, height * 0.28,
                 label, font_size=lbl_fs, color_hex=theme.text_secondary,
                 font_name=body_font)

    # Variance value below bar (header_font, bold)
    sign_str = f"+{variance:.0f}" if is_positive else f"{variance:.0f}"
    _add_textbox(slide, center_x - 0.35, bar_top + bar_h + 0.04, 0.7, 0.22,
                 sign_str, font_size=val_fs, color_hex=bar_color, bold=True,
                 font_name=header_font)

    # Actual and target labels flanking the bar (header_font)
    _add_textbox(slide, left + 0.06, bar_top + bar_h + 0.04, width * 0.44, 0.22,
                 f"Actual: {actual_val:.0f}", font_size=flank_fs, color_hex=theme.text_primary,
                 font_name=header_font)
    _add_textbox(slide, left + width * 0.52, bar_top + bar_h + 0.04, width * 0.44, 0.22,
                 f"Target: {target_val:.0f}", font_size=flank_fs, color_hex=theme.text_secondary,
                 font_name=header_font)


# ===========================================================================
# Phase 2 extension - new Tier A widget renderers
# ===========================================================================

def render_chevron_flow(
    slide, payload: dict, theme,
    left: float, top: float, width: float, height: float,
    header_font: str = "Calibri", body_font: str = "Calibri",
    dark_mode: bool = False
):
    """Horizontal chevron process-flow strip.

    Draws N chevron arrow shapes (MSO_SHAPE.CHEVRON) across the available width.
    Each step contains: badge number (top-left), step title (center), and brief
    description (bottom). Min 2 steps, max 5 steps (extra steps are silently dropped).

    Layout within each chevron:
      * Badge circle region - top 25% of chevron height
      * Title - center 40%
      * Description - bottom 35%
    """
    steps = payload.get("steps", [])
    if not isinstance(steps, list) or not steps:
        steps = []

    steps = steps[:5]
    if len(steps) < 2:
        _add_textbox(slide, left, top, width, height, "Process steps not available",
                     font_size=12, color_hex=theme.text_secondary, font_name=body_font)
        return

    n = len(steps)
    accent_colors = [
        theme.accent_primary,
        theme.accent_secondary if hasattr(theme, "accent_secondary") else theme.accent_primary,
        theme.accent_tertiary if hasattr(theme, "accent_tertiary") else theme.accent_primary,
    ]
    if dark_mode:
        val_color = "#FFFFFF"
        desc_color = "#CCCCCC"
    else:
        val_color = "#FFFFFF"
        desc_color = "#DDDDDD"

    gap = 0.05
    total_gap = gap * (n - 1)
    chev_w = (width - total_gap) / n
    chev_h = height

    for i, step in enumerate(steps):
        cx = left + i * (chev_w + gap)
        cy = top
        fill_color = accent_colors[i % len(accent_colors)]

        if i < n - 1:
            shape = slide.shapes.add_shape(
                MSO_SHAPE.CHEVRON,
                Inches(cx), Inches(cy), Inches(chev_w), Inches(chev_h)
            )
        else:
            shape = slide.shapes.add_shape(
                MSO_SHAPE.PENTAGON,
                Inches(cx), Inches(cy), Inches(chev_w), Inches(chev_h)
            )
        shape.fill.solid()
        shape.fill.fore_color.rgb = _hex_to_rgb(fill_color)
        shape.line.fill.background()

        # Draw badge horizontally in top-left
        badge = str(step.get("badge", f"0{i+1}"))
        badge_font = max(9, min(13, int(chev_h * 22)))
        _add_textbox(slide, cx + 0.1, cy + 0.1, chev_w * 0.4, 0.3,
                     badge, font_size=badge_font, color_hex=val_color, bold=True,
                     font_name=header_font)

        # Draw a single text box for title & description.
        # Inside standard chevrons, place it inside the upper half of the chevron body.
        # For the final pentagon, center it vertically.
        if i < n - 1:
            tx_w = chev_w * 0.76
            tx_h = chev_h * 0.35
            tx_l = cx + chev_w * 0.08
            tx_t = cy + chev_h * 0.14  # mid of the upper half of the chevron
            
            tx_box = slide.shapes.add_textbox(Inches(tx_l), Inches(tx_t), Inches(tx_w), Inches(tx_h))
            tf = tx_box.text_frame
            tf.word_wrap = True
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.01)
            tx_box.rotation = 45.0
        else:
            tx_w = chev_w * 0.85
            tx_h = chev_h * 0.65
            tx_l = cx + (chev_w - tx_w) / 2
            tx_t = cy + (chev_h - tx_h) / 2 + 0.10
            
            tx_box = slide.shapes.add_textbox(Inches(tx_l), Inches(tx_t), Inches(tx_w), Inches(tx_h))
            tf = tx_box.text_frame
            tf.word_wrap = True
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.02)
            tx_box.rotation = 0.0

        title_text = str(step.get("title", ""))
        desc_text = str(step.get("desc", ""))
        
        p_idx = 0
        if title_text:
            p1 = tf.paragraphs[0]
            p1.text = title_text
            p1.font.name = header_font
            p_size = Pt(max(9, min(12, int(chev_h * 24)))) if i < n - 1 else Pt(max(10, min(13, int(chev_h * 26))))
            p1.font.size = p_size
            p1.font.bold = True
            p1.font.color.rgb = _hex_to_rgb(val_color)
            p1.alignment = 2 # Center align
            p_idx += 1
            
        if desc_text:
            p2 = tf.paragraphs[0] if p_idx == 0 else tf.add_paragraph()
            p2.text = desc_text
            p2.font.name = body_font
            d_size = Pt(max(8, min(10, int(chev_h * 15)))) if i < n - 1 else Pt(max(8, min(10, int(chev_h * 16))))
            p2.font.size = d_size
            p2.font.bold = False
            p2.font.color.rgb = _hex_to_rgb(desc_color)
            p2.alignment = 2 # Center align

        icon_name = step.get("icon")
        if icon_name:
            try:
                from ppt_gen.core.icon_library import resolve_icon
                icon_color = "#FFFFFF"
                icon_bytes = resolve_icon(icon_name, icon_color)
                if icon_bytes:
                    import io as _io, tempfile as _tmp
                    from PIL import Image
                    icon_img = Image.open(_io.BytesIO(icon_bytes))
                    icon_sz = min(0.22, chev_h * 0.22)
                    icon_l = cx + chev_w - icon_sz - 0.14
                    icon_t = cy + chev_h - icon_sz - 0.06
                    with _tmp.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                        icon_img.save(tf.name)
                        slide.shapes.add_picture(tf.name, Inches(icon_l), Inches(icon_t),
                                                  Inches(icon_sz), Inches(icon_sz))
            except Exception:
                pass


def render_gantt_strip(
    slide, payload: dict, theme,
    left: float, top: float, width: float, height: float,
    header_font: str = "Calibri", body_font: str = "Calibri",
    dark_mode: bool = False
):
    """Horizontal Gantt chart widget.

    Layout:
      * Left label column (fixed 1.8" or 22% of width, whichever is smaller)
      * Right bar area - each task drawn as a colored rectangle spanning start-end
      * Top header row showing period labels (Q1, Q2, ...)
      * Alternating zebra row backgrounds for readability
      * Thin vertical "today" marker if 'today_period' is present in payload

    Max: 6 tasks, 8 periods.
    """
    tasks = payload.get("tasks", [])
    if not tasks:
        _add_textbox(slide, left, top, width, height, "Roadmap data not available",
                     font_size=12, color_hex=theme.text_secondary, font_name=body_font)
        return

    tasks = tasks[:6]
    periods = payload.get("periods", ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"])
    periods = periods[:8]
    n_periods = len(periods)
    n_tasks = len(tasks)

    label_col_w = min(1.8, width * 0.22)
    bar_area_w = width - label_col_w
    header_row_h = min(0.26, height * 0.12)
    body_h = height - header_row_h
    row_h = body_h / n_tasks
    col_w = bar_area_w / n_periods

    accent_colors = [
        theme.accent_primary,
        theme.accent_secondary if hasattr(theme, "accent_secondary") else theme.accent_primary,
        theme.accent_tertiary if hasattr(theme, "accent_tertiary") else theme.accent_primary,
        theme.accent_primary,
        theme.accent_secondary if hasattr(theme, "accent_secondary") else theme.accent_primary,
        theme.accent_tertiary if hasattr(theme, "accent_tertiary") else theme.accent_primary,
    ]

    if dark_mode:
        label_color = "#CCCCCC"
        period_color = "#AAAAAA"
        zebra_even = theme.card_bg if hasattr(theme, "card_bg") else "#1A1A2E"
        zebra_odd = "#252540"
        header_bg = "#0F0F1F"
    else:
        label_color = theme.text_primary
        period_color = theme.text_secondary
        zebra_even = "#F7F8FA"
        zebra_odd = "#EDEEF2"
        header_bg = "#E8E9EE"

    _add_rect(slide, left + label_col_w, top, bar_area_w, header_row_h,
              fill_hex=header_bg)
    period_font = max(13, min(14, int(col_w * 11)))
    for pi, period in enumerate(periods):
        px = left + label_col_w + pi * col_w
        _add_textbox(slide, px, top, col_w, header_row_h, period,
                     font_size=period_font, color_hex=period_color, bold=True,
                     font_name=header_font)

    for ti, task in enumerate(tasks):
        row_top = top + header_row_h + ti * row_h
        zebra_color = zebra_even if ti % 2 == 0 else zebra_odd

        _add_rect(slide, left, row_top, width, row_h, fill_hex=zebra_color)

        task_name = str(task.get("name", f"Task {ti+1}"))
        label_font = max(13, min(14, int(row_h * 22)))
        _add_textbox(slide, left + 0.06, row_top + row_h * 0.15,
                     label_col_w - 0.08, row_h * 0.7,
                     task_name, font_size=label_font, color_hex=label_color,
                     bold=False, font_name=body_font)

        task_start = max(0, int(task.get("start", 0)))
        task_end = min(n_periods, int(task.get("end", n_periods)))
        if task_end <= task_start:
            task_end = task_start + 1

        bar_color = accent_colors[ti % len(accent_colors)]
        bar_left = left + label_col_w + task_start * col_w + 0.04
        bar_top_pos = row_top + row_h * 0.15
        bar_w = (task_end - task_start) * col_w - 0.08
        bar_h_val = row_h * 0.70
        if bar_w > 0:
            _add_rect(slide, bar_left, bar_top_pos, bar_w, bar_h_val,
                      fill_hex=bar_color)

    today = payload.get("today_period")
    if today is not None and 0 <= int(today) <= n_periods:
        marker_x = left + label_col_w + int(today) * col_w
        marker_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(marker_x - 0.01), Inches(top + header_row_h),
            Inches(0.02), Inches(body_h)
        )
        marker_shape.fill.solid()
        marker_shape.fill.fore_color.rgb = _hex_to_rgb(theme.accent_primary)
        marker_shape.line.fill.background()


def render_venn_diagram(
    slide, payload: dict, theme,
    left: float, top: float, width: float, height: float,
    header_font: str = "Calibri", body_font: str = "Calibri",
    dark_mode: bool = False
):
    """Venn diagram widget - 2-circle or 3-circle layout.

    Circles are drawn as OVAL shapes with 60% transparency fills so overlaps
    are visually apparent. Labels are placed at each circle's center; the
    overlap label is placed at the geometric overlap center.

    2-circle: side-by-side with ~40% overlap
    3-circle: equilateral triangle arrangement with central overlap region
    """
    circles = payload.get("circles", [])
    circles = circles[:3]
    overlap_label = str(payload.get("overlap_label", "") or "")

    if len(circles) < 2:
        _add_textbox(slide, left, top, width, height, "Venn data not available",
                     font_size=12, color_hex=theme.text_secondary, font_name=body_font)
        return

    if dark_mode:
        circle_colors = ["#2A5FA5", "#A03070", "#1A8050"]
        label_color = "#FFFFFF"
        overlap_color = "#FFDD88"
        desc_color = "#BBBBBB"
    else:
        circle_colors = ["#4472C4", "#C0504D", "#70AD47"]
        label_color = "#FFFFFF"
        overlap_color = "#FFFFFF"
        desc_color = theme.text_secondary

    n = len(circles)
    desc_h = height * 0.16
    diagram_h = height - desc_h
    diagram_top = top

    # Split Venn slot horizontally: left for circles, right for text labels
    diag_w = width * 0.55
    text_w = width * 0.40
    text_left = left + width * 0.58

    if n == 2:
        r = min(diagram_h * 0.42, diag_w * 0.32)
        cy = diagram_top + diagram_h * 0.50
        spacing = r * 1.15
        cx1 = left + diag_w / 2 - spacing / 2
        cx2 = left + diag_w / 2 + spacing / 2
        centers = [(cx1, cy), (cx2, cy)]
    else:
        r = min(diagram_h * 0.37, diag_w * 0.28)
        cx_center = left + diag_w / 2
        cy_center = diagram_top + diagram_h * 0.52
        tri_r = r * 0.82
        import math
        centers = []
        for i in range(3):
            angle = math.radians(-90 + i * 120)
            cx_i = cx_center + tri_r * math.cos(angle)
            cy_i = cy_center + tri_r * math.sin(angle)
            centers.append((cx_i, cy_i))

    for i, (cx_i, cy_i) in enumerate(centers):
        oval = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(cx_i - r), Inches(cy_i - r),
            Inches(r * 2), Inches(r * 2)
        )
        oval.fill.solid()
        oval.fill.fore_color.rgb = _hex_to_rgb(circle_colors[i])
        oval.line.color.rgb = _hex_to_rgb(circle_colors[i])
        oval.line.width = Pt(1.5)
        
        from pptx.oxml.ns import qn
        from lxml import etree
        solidFill = oval.fill._xPr.find(qn('a:solidFill'))
        if solidFill is not None:
            srgbClr = solidFill.find(qn('a:srgbClr'))
            if srgbClr is not None:
                alpha = etree.SubElement(srgbClr, qn('a:alpha'))
                alpha.set('val', '60000')

    # Draw descriptions and names outside on the right panel with matching brand colors
    for i, circle in enumerate(circles):
        circle_name = str(circle.get("name", f"Circle {i+1}") if isinstance(circle, dict) else circle)
        circle_desc = str((circle.get("desc", "") or "") if isinstance(circle, dict) else "")

        item_h = diagram_h / n
        item_top = top + i * item_h + 0.1

        # Circle Name in the circle's color
        _add_textbox(slide, text_left, item_top, text_w, item_h * 0.35,
                     circle_name, font_size=13, color_hex=circle_colors[i], bold=True,
                     font_name=header_font)
        # Description in standard text color
        if circle_desc:
            _add_textbox(slide, text_left, item_top + item_h * 0.35, text_w, item_h * 0.60,
                         circle_desc, font_size=11, color_hex=desc_color, bold=False,
                         font_name=body_font)

    if overlap_label:
        cx_overlap = sum(c[0] for c in centers) / n
        cy_overlap = sum(c[1] for c in centers) / n
        ov_w = r * 1.6
        ov_font = max(9, min(13, int(r * 16)))
        _add_textbox(slide, cx_overlap - ov_w / 2, cy_overlap - 0.15, ov_w, 0.30,
                     overlap_label, font_size=ov_font, color_hex=overlap_color, bold=True,
                     font_name=header_font)

    venn_label = str(payload.get("label", ""))
    if venn_label:
        _add_textbox(slide, left, top + diagram_h + 0.04, width, desc_h * 0.9,
                     venn_label, font_size=16, color_hex=desc_color,
                     bold=False, font_name=body_font)


def render_pie_chart(
    slide, payload: Dict[str, Any], theme: "ThemeSettings",
    left: float, top: float, width: float, height: float,
    header_font: str = "Calibri", body_font: str = "Calibri",
    dark_mode: bool = False
):
    from ppt_gen.core.chart_engine_native import _style_legend
    """Editable shape-based native doughnut/pie chart widget.

    Inserts a native XL_CHART_TYPE.DOUGHNUT chart within the bounding box.
    Categories are colored using the theme's palette, with percentage labels.
    """
    labels = payload.get("labels", [])
    values = payload.get("values", [])
    label = payload.get("label", "")

    if not labels or not values or len(labels) != len(values):
        _add_textbox(slide, left, top, width, height, "Pie data not available",
                     font_size=11, color_hex=theme.text_secondary, font_name=body_font)
        return

    # Let's reserve top 12% for the title if label is present
    title_h = height * 0.12 if label else 0.0
    chart_top = top + title_h
    chart_h = height - title_h

    if label:
        _add_textbox(
            slide, left, top, width, title_h,
            label, font_size=11, color_hex=theme.text_primary, bold=True,
            font_name=header_font
        )

    # Compile pptx CategoryChartData
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    
    data = CategoryChartData()
    data.categories = list(labels)
    data.add_series("Share", tuple(float(v) for v in values))

    gf = slide.shapes.add_chart(
        XL_CHART_TYPE.PIE,  # Solid pie chart occupies significantly more visual area
        Inches(left), Inches(chart_top), Inches(width), Inches(chart_h),
        data,
    )
    chart = gf.chart
    chart.has_title = False
    
    plot = chart.plots[0]

    # Color segments
    palette = theme.chart_colors or [
        theme.accent_primary,
        theme.accent_secondary if hasattr(theme, "accent_secondary") else theme.accent_primary,
        theme.accent_tertiary if hasattr(theme, "accent_tertiary") else theme.accent_primary,
    ]
    
    for idx, point in enumerate(plot.series[0].points):
        color = palette[idx % len(palette)]
        try:
            point.format.fill.solid()
            point.format.fill.fore_color.rgb = _hex_to_rgb(color)
            point.format.line.color.rgb = _hex_to_rgb(theme.card_bg if hasattr(theme, "card_bg") else "#FFFFFF")
            point.format.line.width = Pt(1.5)
        except Exception:
            pass

    # Direct labels (category name + percentage) inside/outside slices
    try:
        plot.has_data_labels = True
        dl = plot.data_labels
        dl.show_percentage = True
        dl.show_category_name = True  # show labels directly next to slices
        dl.show_value = False
        dl.number_format = "0%"
        dl.font.size = Pt(8.5)
        dl.font.bold = True
        dl.font.color.rgb = _hex_to_rgb("#FFFFFF" if dark_mode else theme.text_primary)
    except Exception:
        pass

    # Disable legend completely to allow PowerPoint to scale the pie graphic to full container size
    chart.has_legend = False
