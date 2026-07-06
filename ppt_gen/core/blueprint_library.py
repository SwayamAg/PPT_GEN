from typing import List, Literal, Optional, Tuple, Dict
from pydantic import BaseModel, Field

class Slot(BaseModel):
    id: str
    widget: Literal[
        "text", 
        "stat_callout", 
        "icon_text_row", 
        "chart_panel", 
        "table_panel", 
        "numbered_step", 
        "kpi_pill", 
        "priority_card"
    ]
    # Grid area: (col, row, col_span, row_span)
    grid_area: Tuple[float, float, float, float]
    max_chars: Optional[int] = None
    max_items: Optional[int] = None
    # Data shape for synthetic generator
    data_shape: Optional[Literal[
        "single_stat", 
        "paired_comparison", 
        "ranked_bar", 
        "trend_series", 
        "allocation_table"
    ]] = None
    # Group ID: slots with the same group id share a background card panel
    group: Optional[str] = None

class Blueprint(BaseModel):
    archetype: str
    grid: Tuple[int, int] = (12, 8)
    slots: List[Slot]

# Archetypes Library Definitions
ARCHETYPES: Dict[str, Blueprint] = {
    "title_challenge": Blueprint(
        archetype="title_challenge",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0, 12, 1.5), max_chars=120),
            Slot(id="challenge", widget="text", grid_area=(0, 2.5, 12, 4), max_chars=400, group="challenge_box")
        ]
    ),
    "two_column_initiative": Blueprint(
        archetype="two_column_initiative",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0, 12, 1.2), max_chars=120),
            # Left Workstream Card
            Slot(id="left_title", widget="text", grid_area=(0.2, 1.8, 5.6, 0.8), max_chars=60, group="left_card"),
            Slot(id="step1", widget="numbered_step", grid_area=(0.2, 2.8, 5.6, 0.9), max_chars=120, group="left_card"),
            Slot(id="step2", widget="numbered_step", grid_area=(0.2, 3.8, 5.6, 0.9), max_chars=120, group="left_card"),
            Slot(id="step3", widget="numbered_step", grid_area=(0.2, 4.8, 5.6, 0.9), max_chars=120, group="left_card"),
            Slot(id="step4", widget="numbered_step", grid_area=(0.2, 5.8, 5.6, 0.9), max_chars=120, group="left_card"),
            Slot(id="kpi_left", widget="kpi_pill", grid_area=(0.2, 6.9, 5.6, 0.7), max_chars=50, data_shape="single_stat", group="left_card"),
            # Right Workstream Card
            Slot(id="right_title", widget="text", grid_area=(6.2, 1.8, 5.6, 0.8), max_chars=60, group="right_card"),
            Slot(id="step5", widget="numbered_step", grid_area=(6.2, 2.8, 5.6, 0.9), max_chars=120, group="right_card"),
            Slot(id="step6", widget="numbered_step", grid_area=(6.2, 3.8, 5.6, 0.9), max_chars=120, group="right_card"),
            Slot(id="step7", widget="numbered_step", grid_area=(6.2, 4.8, 5.6, 0.9), max_chars=120, group="right_card"),
            Slot(id="step8", widget="numbered_step", grid_area=(6.2, 5.8, 5.6, 0.9), max_chars=120, group="right_card"),
            Slot(id="kpi_right", widget="kpi_pill", grid_area=(6.2, 6.9, 5.6, 0.7), max_chars=50, data_shape="single_stat", group="right_card")
        ]
    ),
    "stat_grid_charts": Blueprint(
        archetype="stat_grid_charts",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0, 12, 1.2), max_chars=120),
            # Four KPI stat boxes
            Slot(id="stat1", widget="stat_callout", grid_area=(0, 1.6, 2.8, 1.6), max_chars=100, data_shape="single_stat", group="s1"),
            Slot(id="stat2", widget="stat_callout", grid_area=(3.0, 1.6, 2.8, 1.6), max_chars=100, data_shape="single_stat", group="s2"),
            Slot(id="stat3", widget="stat_callout", grid_area=(6.0, 1.6, 2.8, 1.6), max_chars=100, data_shape="single_stat", group="s3"),
            Slot(id="stat4", widget="stat_callout", grid_area=(9.0, 1.6, 2.8, 1.6), max_chars=100, data_shape="single_stat", group="s4"),
            # Two Chart blocks
            Slot(id="chart_panel1", widget="chart_panel", grid_area=(0, 3.6, 5.8, 3.9), data_shape="trend_series", group="c1"),
            Slot(id="chart_panel2", widget="chart_panel", grid_area=(6.2, 3.6, 5.8, 3.9), data_shape="paired_comparison", group="c2")
        ]
    ),
    "table_priorities": Blueprint(
        archetype="table_priorities",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0, 12, 1.2), max_chars=120),
            # Table on left
            Slot(id="table_panel", widget="table_panel", grid_area=(0, 1.8, 6.8, 5.7), max_items=5, data_shape="allocation_table", group="tbl_card"),
            # Cards on right
            Slot(id="card1", widget="priority_card", grid_area=(7.2, 1.8, 4.8, 1.2), max_chars=120, group="cr1"),
            Slot(id="card2", widget="priority_card", grid_area=(7.2, 3.3, 4.8, 1.2), max_chars=120, group="cr2"),
            Slot(id="card3", widget="priority_card", grid_area=(7.2, 4.8, 4.8, 1.2), max_chars=120, group="cr3"),
            Slot(id="card4", widget="priority_card", grid_area=(7.2, 6.3, 4.8, 1.2), max_chars=120, group="cr4")
        ]
    ),
    "single_chart_focus": Blueprint(
        archetype="single_chart_focus",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0, 12, 1.2), max_chars=120),
            # Main chart focus on left
            Slot(id="chart_panel", widget="chart_panel", grid_area=(0, 1.8, 7.5, 5.7), data_shape="trend_series", group="chart_card"),
            # Supporting text bullets on right
            Slot(id="bullets", widget="text", grid_area=(8.0, 1.8, 4.0, 5.7), max_chars=400, max_items=4, group="bullet_card")
        ]
    ),
    "comparison_bars": Blueprint(
        archetype="comparison_bars",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0, 12, 1.2), max_chars=120),
            # Pair of benchmark charts
            Slot(id="chart1", widget="chart_panel", grid_area=(0, 1.8, 5.8, 5.7), data_shape="ranked_bar", group="c1"),
            Slot(id="chart2", widget="chart_panel", grid_area=(6.2, 1.8, 5.8, 5.7), data_shape="paired_comparison", group="c2")
        ]
    )
}

def get_blueprint(archetype: str) -> Blueprint:
    """Retrieve the blueprint for a given archetype, raising ValueError if not found."""
    blueprint = ARCHETYPES.get(archetype.lower())
    if not blueprint:
        raise ValueError(f"Unknown archetype: {archetype}. Available: {list(ARCHETYPES.keys())}")
    return blueprint
