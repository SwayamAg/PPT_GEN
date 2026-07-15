"""chart_engine_native.py — Phase F native editable PPTX chart engine.

Mirrors the public surface of chart_engine.render_chart but inserts live,
editable python-pptx chart objects directly onto the slide instead of PNG
images. This makes charts editable in PowerPoint and keeps text crisp at any
zoom.

Supported chart_type values:
  bar / grouped_bar / line / multi_bar / pie / hbar

Unsupported types (waterfall, heatmap) deliberately return False so the
renderer can fall back to the Matplotlib PNG engine.

Every helper returns True if it drew a native chart, False to signal the
caller to fall back.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.chart import (
    XL_CHART_TYPE,
    XL_LEGEND_POSITION,
    XL_LABEL_POSITION,
    XL_TICK_LABEL_POSITION,
    XL_TICK_MARK,
)
from pptx.oxml.ns import qn

from ppt_gen.core.settings import ThemeSettings

logger = logging.getLogger("chart_engine_native")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(*(int(h[i:i + 2], 16) for i in (0, 2, 4)))


def _apply_text_color(plot_or_font_holder, color_hex: str, height_in: float = 4.0):
    """Best-effort: recolor axis/legend font to the theme text color."""
    rgb = _hex_to_rgb(color_hex)
    tick_pt = max(7, min(9, int(height_in * 2.5)))
    try:
        font = plot_or_font_holder.font
        font.color.rgb = rgb
        font.size = Pt(tick_pt)
    except Exception:
        pass


def _style_category_axis(axis, theme: ThemeSettings, *, grid: bool = False, height_in: float = 4.0):
    """Hide axis line & tick labels; optionally add light gridlines."""
    tick_pt = max(7, min(9, int(height_in * 2.5)))
    try:
        axis.has_major_gridlines = grid
        if grid:
            gridlines = axis.major_gridlines
            line = gridlines.format.line
            line.color.rgb = _hex_to_rgb(theme.card_border)
            line.width = Pt(0.5)
        axis.format.line.fill.background()  # hide axis line
        axis.tick_labels.font.size = Pt(tick_pt)
        axis.tick_labels.font.color.rgb = _hex_to_rgb(theme.text_primary)
        axis.tick_mark = XL_TICK_MARK.NONE
    except Exception:
        pass


def _style_value_axis(axis, theme: ThemeSettings, *, grid: bool = True, height_in: float = 4.0):
    tick_pt = max(7, min(9, int(height_in * 2.5)))
    try:
        axis.has_major_gridlines = grid
        if grid:
            gridlines = axis.major_gridlines
            line = gridlines.format.line
            line.color.rgb = _hex_to_rgb(theme.card_border)
            line.width = Pt(0.5)
            line.dash_style = "dash"
        axis.format.line.fill.background()
        axis.tick_labels.font.size = Pt(tick_pt)
        axis.tick_labels.font.color.rgb = _hex_to_rgb(theme.text_secondary)
        axis.tick_mark = XL_TICK_MARK.NONE
    except Exception:
        pass


def _color_series(series, color_hex: str):
    """Fill a single series with a solid brand color and no edge."""
    try:
        fmt = series.format
        fmt.fill.solid()
        fmt.fill.fore_color.rgb = _hex_to_rgb(color_hex)
        fmt.line.fill.background()
    except Exception:
        pass


def _show_data_labels(series, theme: ThemeSettings, *, num_fmt: str = "#,##0",
                      position=None, color_hex=None):
    """Enable data labels with brand-colored numbers."""
    try:
        plot = series.plot
        plot.has_data_labels = True
        dl = plot.data_labels
        dl.number_format = num_fmt
        dl.font.size = Pt(8)
        dl.font.bold = True
        dl.font.color.rgb = _hex_to_rgb(color_hex or theme.text_primary)
        if position is not None:
            dl.position = position
    except Exception:
        pass


def _style_legend(chart, theme: ThemeSettings, position=XL_LEGEND_POSITION.BOTTOM):
    try:
        chart.has_legend = True
        chart.legend.position = position
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(9)
        chart.legend.font.color.rgb = _hex_to_rgb(theme.text_primary)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Chart builders — each returns True on success
# ---------------------------------------------------------------------------

def _native_hbar(slide, chart_data, theme, left, top, width, height):
    """Horizontal ranked bar chart (single series)."""
    labels = chart_data.get("labels", [])
    series = chart_data.get("series", [])
    if not labels or not series:
        return False
    values = series[0].get("values", [])
    if len(values) != len(labels):
        return False

    from pptx.chart.data import CategoryChartData
    data = CategoryChartData()
    data.categories = list(labels)
    data.add_series(series[0].get("name", "Series"), list(values))

    gf = slide.shapes.add_chart(
        XL_CHART_TYPE.BAR_CLUSTERED,
        Inches(left), Inches(top), Inches(width), Inches(height),
        data,
    )
    chart = gf.chart
    chart.has_legend = False

    plot = chart.plots[0]
    plot.gap_width = 60
    _color_series(plot.series[0], theme.accent_primary)
    _show_data_labels(plot.series[0], theme, position=XL_LABEL_POSITION.OUTSIDE_END)

    _style_category_axis(chart.category_axis, theme, height_in=height)
    _style_value_axis(chart.value_axis, theme, grid=False, height_in=height)
    # Hide value-axis tick labels (we have data labels)
    try:
        chart.value_axis.tick_labels.position = XL_TICK_LABEL_POSITION.NONE
    except Exception:
        pass
    return True


def _native_bar(slide, chart_data, theme, left, top, width, height):
    """Vertical ranked bar chart (single series)."""
    labels = chart_data.get("labels", [])
    series = chart_data.get("series", [])
    if not labels or not series:
        return False
    values = series[0].get("values", [])
    if len(values) != len(labels):
        return False

    from pptx.chart.data import CategoryChartData
    data = CategoryChartData()
    data.categories = list(labels)
    data.add_series(series[0].get("name", "Series"), list(values))

    gf = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(left), Inches(top), Inches(width), Inches(height),
        data,
    )
    chart = gf.chart
    chart.has_legend = False

    plot = chart.plots[0]
    plot.gap_width = 80
    _color_series(plot.series[0], theme.accent_primary)
    _show_data_labels(plot.series[0], theme, position=XL_LABEL_POSITION.OUTSIDE_END)

    _style_category_axis(chart.category_axis, theme, height_in=height)
    _style_value_axis(chart.value_axis, theme, grid=True, height_in=height)
    return True


def _native_grouped_bar(slide, chart_data, theme, left, top, width, height):
    """Grouped vertical bar chart (2 series, side by side)."""
    labels = chart_data.get("labels", [])
    series = chart_data.get("series", [])
    if not labels or len(series) < 1:
        return False

    from pptx.chart.data import CategoryChartData
    data = CategoryChartData()
    data.categories = list(labels)
    palette = [theme.accent_secondary, theme.accent_primary]
    for idx, s in enumerate(series[:2]):
        data.add_series(s.get("name", f"Series {idx+1}"), list(s.get("values", [])))

    gf = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(left), Inches(top), Inches(width), Inches(height),
        data,
    )
    chart = gf.chart
    plot = chart.plots[0]
    plot.gap_width = 100
    plot.overlap = -15
    for idx, ser in enumerate(plot.series):
        _color_series(ser, palette[idx % len(palette)])
        _show_data_labels(ser, theme, position=XL_LABEL_POSITION.OUTSIDE_END)

    _style_legend(chart, theme)
    _style_category_axis(chart.category_axis, theme, height_in=height)
    _style_value_axis(chart.value_axis, theme, grid=True, height_in=height)
    return True


def _native_line(slide, chart_data, theme, left, top, width, height):
    """Multi-series line chart with markers."""
    labels = chart_data.get("labels", [])
    series = chart_data.get("series", [])
    if not labels or not series:
        return False

    from pptx.chart.data import CategoryChartData
    data = CategoryChartData()
    data.categories = list(labels)
    for s in series:
        data.add_series(s.get("name", "Series"), list(s.get("values", [])))

    gf = slide.shapes.add_chart(
        XL_CHART_TYPE.LINE_MARKERS,
        Inches(left), Inches(top), Inches(width), Inches(height),
        data,
    )
    chart = gf.chart
    plot = chart.plots[0]
    palette = theme.chart_colors or [theme.accent_primary, theme.accent_secondary,
                                      theme.accent_tertiary]
    for idx, ser in enumerate(plot.series):
        color = palette[idx % len(palette)]
        try:
            ser.format.line.color.rgb = _hex_to_rgb(color)
            ser.format.line.width = Pt(2.25)
            ser.smooth = False
        except Exception:
            pass
        _show_data_labels(ser, theme, position=XL_LABEL_POSITION.ABOVE)

    _style_legend(chart, theme, position=XL_LEGEND_POSITION.TOP)
    _style_category_axis(chart.category_axis, theme, height_in=height)
    _style_value_axis(chart.value_axis, theme, grid=True, height_in=height)
    return True


def _native_multi_bar(slide, chart_data, theme, left, top, width, height):
    """Multi-series vertical bar chart (3+ series share a category axis).

    (PowerPoint has no true small-multiples primitive; multi_bar collapses to
    a single clustered chart. multi_bar is therefore treated like grouped_bar
    here.)
    """
    return _native_grouped_bar(slide, chart_data, theme, left, top, width, height)


def _native_pie(slide, chart_data, theme, left, top, width, height):
    """Pie / doughnut chart (single series, part-to-whole)."""
    labels = chart_data.get("labels", [])
    series = chart_data.get("series", [])
    if not labels or not series:
        return False
    values = series[0].get("values", [])
    if len(values) != len(labels):
        return False

    from pptx.chart.data import CategoryChartData
    data = CategoryChartData()
    data.categories = list(labels)
    data.add_series(series[0].get("name", "Share"), list(values))

    gf = slide.shapes.add_chart(
        XL_CHART_TYPE.DOUGHNUT,
        Inches(left), Inches(top), Inches(width), Inches(height),
        data,
    )
    chart = gf.chart
    plot = chart.plots[0]
    palette = theme.chart_colors or [theme.accent_primary, theme.accent_secondary,
                                      theme.accent_tertiary, theme.accent_quaternary]
    for idx, point in enumerate(plot.series[0].points):
        color = palette[idx % len(palette)]
        try:
            point.format.fill.solid()
            point.format.fill.fore_color.rgb = _hex_to_rgb(color)
            point.format.line.color.rgb = _hex_to_rgb(theme.card_bg)
            point.format.line.width = Pt(1.5)
        except Exception:
            pass

    # Data labels: percent
    try:
        plot.has_data_labels = True
        dl = plot.data_labels
        dl.show_percentage = True
        dl.show_value = False
        dl.show_category_name = False
        dl.number_format = "0%"
        dl.font.size = Pt(9)
        dl.font.bold = True
        dl.font.color.rgb = _hex_to_rgb(theme.text_primary)
    except Exception:
        pass

    _style_legend(chart, theme, position=XL_LEGEND_POSITION.RIGHT)
    return True


# Map chart_type → native builder. Types absent here (waterfall, heatmap) fall
# back to the Matplotlib engine in the renderer.

# ---------------------------------------------------------------------------
# Phase 2B - Native Waterfall (stacked bar trick)
# ---------------------------------------------------------------------------

def _native_waterfall(slide, chart_data: dict, theme, left: float, top: float,
                      width: float, height: float) -> bool:
    """Native editable PPTX waterfall via stacked column chart.

    Technique: COLUMN_STACKED with a transparent 'base' series (the running
    cumulative floor) and a visible 'delta' series. Connecting lines drawn as
    thin rectangles. Returns True on success.
    """
    labels = chart_data.get("labels", [])
    series = chart_data.get("series", [])
    start_value = float(chart_data.get("start_value", 0))
    if not labels or not series:
        return False

    raw_values = [float(v) for v in series[0].get("values", [])]
    if len(raw_values) != len(labels):
        return False

    n = len(raw_values)
    bases = []
    deltas = []

    running = start_value
    for i, val in enumerate(raw_values):
        if i == 0 or i == n - 1:
            bases.append(0.0)
            deltas.append(val)
        else:
            is_pos = val >= 0
            if is_pos:
                bases.append(running)
                deltas.append(val)
            else:
                bases.append(running + val)
                deltas.append(abs(val))
            running += val

    from pptx.chart.data import CategoryChartData
    data = CategoryChartData()
    data.categories = list(labels)
    data.add_series("Base",  tuple(bases))
    data.add_series("Delta", tuple(deltas))

    gf = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_STACKED,
        Inches(left), Inches(top), Inches(width), Inches(height),
        data,
    )
    chart = gf.chart
    chart.has_legend = False

    plot = chart.plots[0]
    plot.gap_width = 30

    base_series = plot.series[0]
    try:
        base_series.format.fill.background()
        base_series.format.line.fill.background()
    except Exception:
        pass

    delta_series = plot.series[1]
    try:
        delta_series.format.fill.solid()
        delta_series.format.fill.fore_color.rgb = _hex_to_rgb(theme.accent_primary)
        delta_series.format.line.fill.background()
    except Exception:
        pass

    _style_category_axis(chart.category_axis, theme, grid=False)
    _style_value_axis(chart.value_axis, theme, grid=True)
    return True


# ---------------------------------------------------------------------------
# Phase 2C - Native Heatmap (formatted PPTX table)
# ---------------------------------------------------------------------------

def _native_heatmap(slide, chart_data: dict, theme, left: float, top: float,
                    width: float, height: float) -> bool:
    """Native editable heatmap as a styled python-pptx table.

    Cell backgrounds are interpolated between a light base color and
    accent_primary based on normalized cell value.
    """
    col_labels = chart_data.get("labels", [])
    row_labels = chart_data.get("row_labels", [])
    series = chart_data.get("series", [])
    if not col_labels or not row_labels or not series:
        return False

    n_rows = len(row_labels)
    n_cols = len(col_labels)
    matrix = [s.get("values", []) for s in series]

    all_vals = [v for row_vals in matrix for v in row_vals if v is not None]
    if not all_vals:
        return False
    v_min, v_max = min(all_vals), max(all_vals)
    v_range = max(v_max - v_min, 1e-9)

    rows_total = n_rows + 1
    cols_total = n_cols + 1

    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor

    tbl = slide.shapes.add_table(
        rows_total, cols_total,
        Inches(left), Inches(top), Inches(width), Inches(height)
    ).table

    label_col_w = Inches(width * 0.22)
    data_col_w = Inches((width - width * 0.22) / n_cols)
    tbl.columns[0].width = label_col_w
    for ci in range(1, cols_total):
        tbl.columns[ci].width = data_col_w

    hdr_row_h = Inches(height * 0.14)
    data_row_h = Inches((height - height * 0.14) / n_rows)
    tbl.rows[0].height = hdr_row_h
    for ri in range(1, rows_total):
        tbl.rows[ri].height = data_row_h

    def hex_to_tuple(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    try:
        base_rgb = hex_to_tuple("#F0F4FA")
        accent_rgb = hex_to_tuple(theme.accent_primary)
    except Exception:
        base_rgb = (240, 244, 250)
        accent_rgb = (68, 114, 196)

    header_hex = theme.accent_primary
    header_text = "#FFFFFF"
    cell_text = theme.text_primary

    corner = tbl.cell(0, 0)
    corner.fill.solid()
    corner.fill.fore_color.rgb = _hex_to_rgb(header_hex)

    for ci, col_lbl in enumerate(col_labels):
        cell = tbl.cell(0, ci + 1)
        cell.fill.solid()
        cell.fill.fore_color.rgb = _hex_to_rgb(header_hex)
        tf = cell.text_frame
        p = tf.paragraphs[0]
        p.text = str(col_lbl)
        p.font.size = Pt(9)
        p.font.bold = True
        p.font.color.rgb = _hex_to_rgb(header_text)

    for ri, row_lbl in enumerate(row_labels):
        row_cell = tbl.cell(ri + 1, 0)
        row_cell.fill.solid()
        row_cell.fill.fore_color.rgb = _hex_to_rgb(header_hex)
        rp = row_cell.text_frame.paragraphs[0]
        rp.text = str(row_lbl)
        rp.font.size = Pt(9)
        rp.font.bold = True
        rp.font.color.rgb = _hex_to_rgb(header_text)

        row_vals = matrix[ri] if ri < len(matrix) else []
        for ci in range(n_cols):
            val = float(row_vals[ci]) if ci < len(row_vals) else 0.0
            norm = (val - v_min) / v_range

            r = int(base_rgb[0] + norm * (accent_rgb[0] - base_rgb[0]))
            g = int(base_rgb[1] + norm * (accent_rgb[1] - base_rgb[1]))
            b = int(base_rgb[2] + norm * (accent_rgb[2] - base_rgb[2]))

            data_cell = tbl.cell(ri + 1, ci + 1)
            data_cell.fill.solid()
            data_cell.fill.fore_color.rgb = RGBColor(r, g, b)
            dp = data_cell.text_frame.paragraphs[0]
            dp.text = f"{val:.0f}"
            dp.font.size = Pt(9)
            dp.font.bold = norm > 0.6
            txt_color = "#FFFFFF" if norm > 0.55 else cell_text
            dp.font.color.rgb = _hex_to_rgb(txt_color)

    return True


# Map chart_type to native builder. Types absent here fall back to Matplotlib.
_NATIVE_BUILDERS = {
    "hbar":         _native_hbar,
    "bar":          _native_bar,
    "grouped_bar":  _native_grouped_bar,
    "line":         _native_line,
    "multi_bar":    _native_multi_bar,
    "pie":          _native_pie,
    "waterfall":    _native_waterfall,
    "heatmap":      _native_heatmap,
}


def render_native_chart(
    chart_type: str,
    chart_data: Dict[str, Any],
    slide,
    theme: ThemeSettings,
    left: float,
    top: float,
    width: float,
    height: float,
) -> bool:
    """Insert a native editable PPTX chart onto ``slide``.

    Returns True if a native chart was drawn; False if the type is unsupported
    or the data is malformed (caller should fall back to Matplotlib).
    """
    builder = _NATIVE_BUILDERS.get(chart_type)
    if builder is None:
        logger.debug("No native builder for %r; falling back to Matplotlib.", chart_type)
        return False
    try:
        return builder(slide, chart_data, theme, left, top, width, height)
    except Exception as e:
        logger.warning("Native chart render failed (%s); falling back to Matplotlib.", e)
        return False
