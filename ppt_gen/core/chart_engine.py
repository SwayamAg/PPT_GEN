import logging
from pathlib import Path
from typing import Dict, List, Any
import matplotlib
matplotlib.use('Agg')  # Headless backend to prevent display errors
import matplotlib.pyplot as plt

from ppt_gen.core.settings import ThemeSettings

logger = logging.getLogger("chart_engine")

def apply_base_style(fig, ax, theme: ThemeSettings, height_in: float = 4.0):
    """Apply consistent background and text colors from the theme."""
    fig.patch.set_facecolor('none')  # Transparent figure background
    ax.set_facecolor('none')         # Transparent axes background
    
    # Text and grid colors
    text_color = theme.text_primary
    grid_color = theme.accent_quaternary
    
    # Configure spines
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # Scale tick label size proportionally to available chart height
    # (small chart slots get smaller tick labels to prevent collisions)
    tick_size = max(7, min(10, int(height_in * 2.5)))
    ax.tick_params(colors=text_color, labelsize=tick_size)
    ax.yaxis.grid(True, linestyle='--', alpha=0.5, color=grid_color)
    ax.set_axisbelow(True)

def render_ranked_bar(
    labels: List[str],
    values: List[float],
    output_path: Path,
    theme: ThemeSettings,
    width_in: float = 6.0,
    height_in: float = 4.0
):
    """Render a horizontal bar chart sorted for benchmarking."""
    fig, ax = plt.subplots(figsize=(width_in, height_in))
    apply_base_style(fig, ax, theme, height_in)
    ax.yaxis.grid(False)  # Horizontal grid is not needed for horizontal bars
    ax.xaxis.grid(True, linestyle='--', alpha=0.5, color=theme.accent_quaternary)
    
    # Colors: highlight 'Our Target' or 'Our Share'
    colors = []
    for label in labels:
        if "our" in label.lower() or "we" in label.lower():
            colors.append(theme.accent_primary)  # Primary brand color
        else:
            colors.append(theme.accent_secondary)  # Muted secondary color
            
    bars = ax.barh(labels, values, color=colors, height=0.6, edgecolor='none')
    ax.invert_yaxis()  # Put top ranked at the top
    
    # Scale fonts relative to chart height
    lbl_size = max(7, min(10, int(height_in * 2.2)))
    
    # Add values directly to the right of bars
    for bar in bars:
        width = bar.get_width()
        ax.text(
            width + (max(values) * 0.02),
            bar.get_y() + bar.get_height()/2,
            f"{width:,.1f}" if width % 1 != 0 else f"{int(width):,}",
            va='center',
            ha='left',
            color=theme.text_primary,
            fontweight='bold',
            fontsize=lbl_size
        )
        
    plt.tight_layout()
    plt.savefig(output_path, transparent=True, dpi=300, bbox_inches='tight')
    plt.close()

def render_paired_comparison(
    labels: List[str],
    series: List[Dict[str, Any]],
    output_path: Path,
    theme: ThemeSettings,
    width_in: float = 6.0,
    height_in: float = 4.0
):
    """Render a side-by-side grouped vertical bar chart comparing two paths/states."""
    fig, ax = plt.subplots(figsize=(width_in, height_in))
    apply_base_style(fig, ax, theme, height_in)
    
    x = range(len(labels))
    bar_width = 0.35
    lbl_size = max(7, min(10, int(height_in * 2.2)))
    
    # If we have only 1 series, draw a simple vertical bar
    if len(series) == 1:
        s = series[0]
        color = theme.accent_primary
        bars = ax.bar(x, s["values"], width=bar_width, color=color, label=s["name"], edgecolor='none')
        # Add labels
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2,
                height + (max(s["values"]) * 0.02),
                f"{height:,.1f}" if height % 1 != 0 else f"{int(height):,}",
                ha='center',
                va='bottom',
                color=theme.text_primary,
                fontsize=lbl_size
            )
    else:
        # Grouped bar chart (e.g. Us vs Competitor)
        for idx, s in enumerate(series[:2]):  # Limit to 2 series for comparison cleanliness
            offset = (idx - 0.5) * bar_width
            color = theme.accent_primary if idx == 1 else theme.text_secondary
            x_positions = [pos + offset for pos in x]
            bars = ax.bar(x_positions, s["values"], width=bar_width, color=color, label=s["name"], edgecolor='none')
            
            # Add data labels on top of bars
            for bar in bars:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width()/2,
                    height + (height * 0.01),
                    f"{height:,.1f}" if height % 1 != 0 else f"{int(height):,}",
                    ha='center',
                    va='bottom',
                    color=theme.text_primary,
                    fontsize=max(6, lbl_size - 1)
                )
                
        ax.legend(frameon=False, loc='upper right', labelcolor=theme.text_primary, fontsize=lbl_size)
        
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=lbl_size)
    
    plt.tight_layout()
    plt.savefig(output_path, transparent=True, dpi=300, bbox_inches='tight')
    plt.close()

def render_trend_line(
    labels: List[str],
    series: List[Dict[str, Any]],
    output_path: Path,
    theme: ThemeSettings,
    width_in: float = 6.0,
    height_in: float = 4.0
):
    """Render a smooth trend line series comparing a current path with targets."""
    fig, ax = plt.subplots(figsize=(width_in, height_in))
    apply_base_style(fig, ax, theme, height_in)
    
    lbl_size = max(7, min(10, int(height_in * 2.2)))
    
    for idx, s in enumerate(series):
        # Muted path for base, highlighted solid path for target
        is_target = "target" in s["name"].lower() or "scenario" in s["name"].lower() or "play" in s["name"].lower()
        color = theme.accent_primary if is_target or idx == 1 else theme.text_secondary
        linestyle = '-' if is_target or idx == 1 else '--'
        linewidth = 2.5 if is_target or idx == 1 else 1.5
        
        ax.plot(
            labels,
            s["values"],
            marker='o',
            color=color,
            linestyle=linestyle,
            linewidth=linewidth,
            label=s["name"]
        )
        
        # Add labels to start and end points of target
        for i, val in enumerate(s["values"]):
            if i == 0 or i == len(s["values"]) - 1:
                ax.text(
                    i,
                    val + (max(s["values"]) * 0.03),
                    f"{val:,.1f}" if val % 1 != 0 else f"{int(val):,}",
                    ha='center',
                    va='bottom',
                    color=color,
                    fontweight='bold',
                    fontsize=lbl_size
                )
                
    ax.legend(frameon=False, loc='upper left', labelcolor=theme.text_primary, fontsize=lbl_size)
    ax.tick_params(labelsize=lbl_size)
    
    plt.tight_layout()
    plt.savefig(output_path, transparent=True, dpi=300, bbox_inches='tight')
    plt.close()

def render_multi_bar(
    labels: List[str],
    series: List[Dict[str, Any]],
    output_path: Path,
    theme: ThemeSettings,
    width_in: float = 6.0,
    height_in: float = 4.0
):
    """Render multiple small subplots side-by-side sharing a legend (McKinsey dashboard style)."""
    # E.g. If we have 2 series, we draw 2 subplots side-by-side
    fig, axes = plt.subplots(1, len(series), figsize=(width_in, height_in))
    lbl_size = max(7, min(10, int(height_in * 2.2)))
    title_size = max(8, min(11, int(height_in * 2.4)))
    
    # Handle single subplot case fallback
    if len(series) == 1:
        axes = [axes]
        
    for idx, (ax, s) in enumerate(zip(axes, series)):
        # Apply standard style to each axis
        apply_base_style(fig, ax, theme, height_in)
        ax.set_title(s["name"], color=theme.text_primary, fontsize=title_size, pad=10, fontweight='bold')
        
        x = range(len(labels))
        color = theme.accent_primary if idx == 0 else theme.accent_secondary
        
        bars = ax.bar(x, s["values"], width=0.5, color=color, edgecolor='none')
        
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2,
                height + (height * 0.02),
                f"{height:,.1f}" if height % 1 != 0 else f"{int(height):,}",
                ha='center',
                va='bottom',
                color=theme.text_primary,
                fontsize=max(6, lbl_size - 1)
            )
            
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=lbl_size)
        
    plt.tight_layout()
    plt.savefig(output_path, transparent=True, dpi=300, bbox_inches='tight')
    plt.close()


def render_waterfall(
    labels: List[str],
    values: List[float],
    output_path: Path,
    theme: ThemeSettings,
    width_in: float = 6.0,
    height_in: float = 4.0
):
    """
    Render a waterfall chart via sequential floating bars using bottom= offsets.
    values[0]  = start value (full bar from 0)
    values[1:-1] = delta segments (positive / negative, floating)
    values[-1] = end value (full bar from 0)
    Brand colors: accent_secondary for positive, accent_tertiary for negative,
    accent_primary for start/end totals.
    """
    import numpy as np

    n = len(values)
    x = range(n)
    running = 0.0
    bottoms = []
    bar_vals = []
    colors = []

    for i, v in enumerate(values):
        if i == 0 or i == n - 1:
            # Start and end bars anchor at 0
            bottoms.append(0)
            bar_vals.append(v)
            colors.append(theme.accent_primary)
            if i == 0:
                running = v
        else:
            # Floating delta bar
            if v >= 0:
                bottoms.append(running)
                bar_vals.append(v)
                colors.append(theme.accent_secondary)
            else:
                bottoms.append(running + v)
                bar_vals.append(abs(v))
                colors.append(theme.accent_tertiary)
            running += v

    fig, ax = plt.subplots(figsize=(width_in, height_in))
    apply_base_style(fig, ax, theme, height_in)
    
    lbl_size = max(7, min(10, int(height_in * 2.2)))

    bars = ax.bar(x, bar_vals, bottom=bottoms, color=colors, width=0.6, edgecolor='none')

    # Connector lines between bars
    for i in range(n - 1):
        top_i = bottoms[i] + bar_vals[i]
        ax.plot([i + 0.3, i + 0.7], [top_i, top_i],
                color=theme.text_secondary, linewidth=0.8, linestyle='--', alpha=0.6)

    # Value labels
    for i, (bar, v) in enumerate(zip(bars, values)):
        label_y = bar.get_y() + bar.get_height() + (max(values) * 0.02 if max(values) > 0 else 1)
        ax.text(bar.get_x() + bar.get_width() / 2, label_y,
                f"+{v:.0f}" if v > 0 and 0 < i < n - 1 else f"{v:.0f}",
                ha='center', va='bottom',
                color=theme.text_primary, fontweight='bold', fontsize=lbl_size)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=lbl_size)
    ax.axhline(0, color=theme.text_secondary, linewidth=0.5)

    plt.tight_layout()
    plt.savefig(output_path, transparent=True, dpi=300, bbox_inches='tight')
    plt.close()


def render_heatmap(
    labels: List[str],       # column labels (x-axis)
    series: List[Dict[str, Any]],  # each series = one row
    output_path: Path,
    theme: ThemeSettings,
    width_in: float = 6.0,
    height_in: float = 4.0
):
    """
    Render a heatmap using imshow with a brand-derived colormap.
    series[i]['name'] = row label; series[i]['values'] = float list across columns.
    """
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap

    row_labels = [s["name"] for s in series]
    matrix = [s["values"] for s in series]
    data = np.array(matrix, dtype=float)

    # Brand-derived colormap: light card_bg → accent_primary
    def hex2rgb01(h: str):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

    cmap = LinearSegmentedColormap.from_list(
        "brand",
        [hex2rgb01(theme.card_bg), hex2rgb01(theme.accent_primary)]
    )

    fig, ax = plt.subplots(figsize=(width_in, height_in))
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')

    im = ax.imshow(data, cmap=cmap, aspect='auto')
    lbl_size = max(7, min(10, int(height_in * 2.2)))

    # Tick labels
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, color=theme.text_primary, fontsize=lbl_size)
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels, color=theme.text_primary, fontsize=lbl_size)

    # Remove spines
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)

    # Cell value annotations
    vmin, vmax = data.min(), data.max()
    for row_i in range(data.shape[0]):
        for col_i in range(data.shape[1]):
            val = data[row_i, col_i]
            norm = (val - vmin) / max(vmax - vmin, 0.001)
            txt_color = theme.background if norm > 0.5 else theme.text_primary
            ax.text(col_i, row_i, f"{val:.0f}",
                    ha='center', va='center', fontsize=lbl_size,
                    color=txt_color, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, transparent=True, dpi=300, bbox_inches='tight')
    plt.close()

def render_chart(
    chart_type: str,
    chart_data: Dict[str, Any],
    output_path: Path,
    theme: ThemeSettings,
    width_in: float = 6.0,
    height_in: float = 4.0
):
    """Main entrypoint to generate and save a chart based on type and input data."""
    labels = chart_data.get("labels", [])
    series = chart_data.get("series", [])
    
    if not labels or not series:
        logger.warning(f"Empty chart data for output: {output_path}")
        return
        
    output_path.parent.mkdir(exist_ok=True, parents=True)
    
    try:
        if chart_type == "bar":
            # For 1D series, ranked_bar
            values = series[0].get("values", [])
            render_ranked_bar(labels, values, output_path, theme, width_in, height_in)
        elif chart_type == "grouped_bar":
            render_paired_comparison(labels, series, output_path, theme, width_in, height_in)
        elif chart_type == "line":
            render_trend_line(labels, series, output_path, theme, width_in, height_in)
        elif chart_type == "multi_bar":
            render_multi_bar(labels, series, output_path, theme, width_in, height_in)
        elif chart_type == "waterfall":
            # Waterfall expects values[0]=start, values[1:-1]=deltas, values[-1]=end
            values = series[0].get("values", [])
            render_waterfall(labels, values, output_path, theme, width_in, height_in)
        elif chart_type == "heatmap":
            render_heatmap(labels, series, output_path, theme, width_in, height_in)
        else:
            logger.error(f"Unknown chart type {chart_type}. Rendering line trend as fallback.")
            render_trend_line(labels, series, output_path, theme, width_in, height_in)
    except Exception as e:
        logger.error(f"Failed to render chart: {str(e)}")
        # Generate an empty error plot
        fig, ax = plt.subplots(figsize=(width_in, height_in))
        ax.text(0.5, 0.5, f"Chart Render Error:\n{str(e)}", ha='center', va='center', color='red')
        plt.savefig(output_path, transparent=True, dpi=100)
        plt.close()
