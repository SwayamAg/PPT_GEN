import logging
from pathlib import Path
from typing import Dict, List, Any
import matplotlib
matplotlib.use('Agg')  # Headless backend to prevent display errors
import matplotlib.pyplot as plt

from ppt_gen.core.settings import ThemeSettings

logger = logging.getLogger("chart_engine")

def apply_base_style(fig, ax, theme: ThemeSettings):
    """Apply consistent background and text colors from the theme."""
    fig.patch.set_facecolor('none')  # Transparent figure background
    ax.set_facecolor('none')         # Transparent axes background
    
    # Text and grid colors
    text_color = theme.text_primary
    grid_color = theme.accent_quaternary
    
    # Configure spines
    for spine in ax.spines.values():
        spine.set_visible(False)
        
    ax.tick_params(colors=text_color, labelsize=10)
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
    apply_base_style(fig, ax, theme)
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
            fontsize=10
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
    apply_base_style(fig, ax, theme)
    
    x = range(len(labels))
    bar_width = 0.35
    
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
                fontsize=9
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
                    fontsize=8
                )
                
        ax.legend(frameon=False, loc='upper right', labelcolor=theme.text_primary, fontsize=9)
        
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    
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
    apply_base_style(fig, ax, theme)
    
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
                    fontsize=9
                )
                
    ax.legend(frameon=False, loc='upper left', labelcolor=theme.text_primary, fontsize=9)
    
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
    
    # Handle single subplot case fallback
    if len(series) == 1:
        axes = [axes]
        
    for idx, (ax, s) in enumerate(zip(axes, series)):
        # Apply standard style to each axis
        apply_base_style(fig, ax, theme)
        ax.set_title(s["name"], color=theme.text_primary, fontsize=10, pad=10, fontweight='bold')
        
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
                fontsize=8
            )
            
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        
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
