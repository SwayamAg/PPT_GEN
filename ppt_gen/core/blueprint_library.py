from typing import List, Literal, Optional, Tuple, Dict
from pydantic import BaseModel, Field


class Slot(BaseModel):
    id: str
    widget: Literal[
        "text",
        "stat_callout",
        "kpi_card",
        "icon_text_row",
        "chart_panel",
        "table_panel",
        "numbered_step",
        "kpi_pill",
        "priority_card",
        "progress_indicator",
        "growth_arrow",
        "benchmark_bar",
        "market_share_strip",
        "scorecard",
        "matrix_view",
        "variance_graphic",
        # Phase C: new widgets
        "eyebrow",
        "footer",
        # Phase 2 extension: new visual widgets
        "chevron_flow",
        "gantt_strip",
        "venn_diagram",
        "pie_chart",
    ]
    # Grid area: (col, row, col_span, row_span)
    grid_area: Tuple[float, float, float, float]
    max_chars: Optional[int] = None
    max_items: Optional[int] = None
    # ÃÂÃÂÃÂÃÂ§7.3 ÃÂÃÂ¢ÃÂÃÂ" semantic shape of the data, declared by archetype (never by LLM)
    data_pattern: Optional[Literal[
        "single_value",
        "comparison_pair",
        "comparison_rank",
        "trend",
        "part_to_whole",
        "deviation_from_target",
        "cumulative_buildup",
        "distribution_grid",
        "prioritization_matrix",
        "allocation_table",
        # Phase 2 extension: new data patterns
        "gantt_timeline",
        "overlap_analysis",
        "process_sequence",
    ]] = None
    # ÃÂÃÂÃÂÃÂ§6.1 ÃÂÃÂ¢ÃÂÃÂ" resolved by select_render_style() at build time; if set here the selector is skipped
    render_style: Optional[str] = None
    # Group ID: slots with the same group id share a background card panel
    group: Optional[str] = None


class Blueprint(BaseModel):
    archetype: str
    grid: Tuple[int, int] = (12, 8)
    # Phase D: "title" archetypes (cover/closing) render on a dark background
    # when the theme declares title_slide_background (e.g. navy theme).
    background: Literal["content", "title"] = "content"
    slots: List[Slot]


# ---------------------------------------------------------------------------
# Archetypes Library
# ---------------------------------------------------------------------------
ARCHETYPES: Dict[str, Blueprint] = {
    # ── Phase H Cover Archetypes ───────────────────────────────────────────
    "executive_cover": Blueprint(
        archetype="executive_cover",
        background="title",
        slots=[
            Slot(id="eyebrow", widget="eyebrow", grid_area=(0.5, 0.6, 11, 0.5), max_chars=60),
            Slot(id="title", widget="text", grid_area=(0.5, 1.8, 11, 2.2), max_chars=140),
            Slot(id="subtitle", widget="text", grid_area=(0.5, 4.8, 11, 0.9), max_chars=160),
            Slot(id="kpi1", widget="kpi_card", grid_area=(0.5, 6.0, 3.6, 1.3),
                 max_chars=80, data_pattern="single_value", group="cv1"),
            Slot(id="kpi2", widget="kpi_card", grid_area=(4.4, 6.0, 3.6, 1.3),
                 max_chars=80, data_pattern="single_value", group="cv2"),
            Slot(id="kpi3", widget="kpi_card", grid_area=(8.3, 6.0, 3.6, 1.3),
                 max_chars=80, data_pattern="single_value", group="cv3"),
            Slot(id="footer", widget="footer", grid_area=(0.5, 7.4, 11, 0.4), max_chars=120),
        ]
    ),
    "closing_takeaways": Blueprint(
        archetype="closing_takeaways",
        background="title",
        slots=[
            Slot(id="eyebrow", widget="eyebrow", grid_area=(0.5, 0.6, 11, 0.5), max_chars=60),
            Slot(id="title", widget="text", grid_area=(0.5, 1.4, 11, 1.0), max_chars=120),
            Slot(id="takeaway1", widget="priority_card", grid_area=(0.5, 2.8, 5.5, 2.1),
                 max_chars=160, group="tk1"),
            Slot(id="takeaway2", widget="priority_card", grid_area=(6.2, 2.8, 5.5, 2.1),
                 max_chars=160, group="tk2"),
            Slot(id="takeaway3", widget="priority_card", grid_area=(0.5, 5.1, 5.5, 2.1),
                 max_chars=160, group="tk3"),
            Slot(id="takeaway4", widget="priority_card", grid_area=(6.2, 5.1, 5.5, 2.1),
                 max_chars=160, group="tk4"),
            Slot(id="footer", widget="footer", grid_area=(0.5, 7.4, 11, 0.4), max_chars=120),
        ]
    ),

    # ── Standard High-Density Dashboards ────────────────────────────────────
    "title_challenge": Blueprint(
        archetype="title_challenge",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0.1, 12, 0.7), max_chars=120),
            Slot(id="subtitle", widget="text", grid_area=(0, 0.8, 12, 0.4), max_chars=120),
            # Row 1 KPIs
            Slot(id="kpi1", widget="kpi_card", grid_area=(0, 1.3, 3.8, 1.5),
                 max_chars=80, data_pattern="single_value", group="tc_k1"),
            Slot(id="kpi2", widget="growth_arrow", grid_area=(4.1, 1.3, 3.8, 1.5),
                 max_chars=80, data_pattern="single_value", group="tc_k2"),
            Slot(id="kpi3", widget="variance_graphic", grid_area=(8.2, 1.3, 3.8, 1.5),
                 max_chars=80, data_pattern="deviation_from_target", group="tc_k3"),
            # Row 2 Text & Actions
            Slot(id="challenge", widget="text", grid_area=(0, 2.9, 7.9, 4.6), max_chars=350, group="tc_ch"),
            Slot(id="action", widget="numbered_step", grid_area=(8.2, 2.9, 3.8, 4.6), max_chars=120, group="tc_act"),
        ]
    ),
    "two_column_initiative": Blueprint(
        archetype="two_column_initiative",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0.1, 12, 0.7), max_chars=120),
            Slot(id="subtitle", widget="text", grid_area=(0, 0.8, 12, 0.4), max_chars=120),
            # Column 1
            Slot(id="kpi1", widget="kpi_card", grid_area=(0, 1.3, 5.8, 1.3),
                 max_chars=80, data_pattern="single_value", group="col1_k"),
            Slot(id="chart1", widget="chart_panel", grid_area=(0, 2.7, 5.8, 3.0),
                 data_pattern="comparison_rank", group="col1_ch"),
            Slot(id="bullets1", widget="text", grid_area=(0, 5.8, 5.8, 1.7), max_chars=250, max_items=3, group="col1_b"),
            # Column 2
            Slot(id="kpi2", widget="kpi_card", grid_area=(6.2, 1.3, 5.8, 1.3),
                 max_chars=80, data_pattern="single_value", group="col2_k"),
            Slot(id="chart2", widget="chart_panel", grid_area=(6.2, 2.7, 5.8, 3.0),
                 data_pattern="trend", group="col2_ch"),
            Slot(id="bullets2", widget="text", grid_area=(6.2, 5.8, 5.8, 1.7), max_chars=250, max_items=3, group="col2_b"),
        ]
    ),
    "stat_grid_charts": Blueprint(
        archetype="stat_grid_charts",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0.1, 12, 0.7), max_chars=120),
            Slot(id="subtitle", widget="text", grid_area=(0, 0.8, 12, 0.4), max_chars=120),
            # Row 1: 3 KPI stats
            Slot(id="kpi1", widget="kpi_card", grid_area=(0, 1.3, 3.8, 1.4),
                 max_chars=80, data_pattern="single_value", group="sg_k1"),
            Slot(id="kpi2", widget="kpi_card", grid_area=(4.1, 1.3, 3.8, 1.4),
                 max_chars=80, data_pattern="single_value", group="sg_k2"),
            Slot(id="kpi3", widget="kpi_card", grid_area=(8.2, 1.3, 3.8, 1.4),
                 max_chars=80, data_pattern="single_value", group="sg_k3"),
            # Row 2: 2 stacked charts
            Slot(id="chart1", widget="chart_panel", grid_area=(0, 2.8, 5.8, 2.9),
                 data_pattern="trend", group="sg_ch1"),
            Slot(id="chart2", widget="chart_panel", grid_area=(6.2, 2.8, 5.8, 2.9),
                 data_pattern="comparison_rank", group="sg_ch2"),
            # Row 3: 3 priority takeaways
            Slot(id="takeaway1", widget="priority_card", grid_area=(0, 5.8, 3.8, 1.7), max_chars=160, group="sg_t1"),
            Slot(id="takeaway2", widget="priority_card", grid_area=(4.1, 5.8, 3.8, 1.7), max_chars=160, group="sg_t2"),
            Slot(id="takeaway3", widget="priority_card", grid_area=(8.2, 5.8, 3.8, 1.7), max_chars=160, group="sg_t3"),
        ]
    ),
    "table_priorities": Blueprint(
        archetype="table_priorities",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0.1, 12, 0.7), max_chars=120),
            Slot(id="subtitle", widget="text", grid_area=(0, 0.8, 12, 0.4), max_chars=120),
            # Row 1 top KPIs
            Slot(id="kpi1", widget="kpi_card", grid_area=(0, 1.3, 5.8, 1.3),
                 max_chars=80, data_pattern="single_value", group="tp_k1"),
            Slot(id="kpi2", widget="kpi_card", grid_area=(6.2, 1.3, 5.8, 1.3),
                 max_chars=80, data_pattern="single_value", group="tp_k2"),
            # Row 2 Table & Variance check
            Slot(id="table", widget="table_panel", grid_area=(0, 2.7, 7.9, 3.0),
                 max_items=5, data_pattern="allocation_table", group="tp_tbl"),
            Slot(id="var_metric", widget="variance_graphic", grid_area=(8.2, 2.7, 3.8, 3.0),
                 data_pattern="deviation_from_target", group="tp_var"),
            # Row 3 Step milestones
            Slot(id="step1", widget="numbered_step", grid_area=(0, 5.8, 3.8, 1.7), max_chars=120, group="tp_s1"),
            Slot(id="step2", widget="numbered_step", grid_area=(4.1, 5.8, 3.8, 1.7), max_chars=120, group="tp_s2"),
            Slot(id="step3", widget="numbered_step", grid_area=(8.2, 5.8, 3.8, 1.7), max_chars=120, group="tp_s3"),
        ]
    ),
    "single_chart_focus": Blueprint(
        archetype="single_chart_focus",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0.1, 12, 0.7), max_chars=120),
            Slot(id="subtitle", widget="text", grid_area=(0, 0.8, 12, 0.4), max_chars=120),
            # Row 1 chart + KPI stack
            Slot(id="chart_panel", widget="chart_panel", grid_area=(0, 1.3, 7.9, 4.2),
                 data_pattern="cumulative_buildup", group="sc_ch"),
            Slot(id="kpi_stack", widget="scorecard", grid_area=(8.2, 1.3, 3.8, 4.2),
                 data_pattern="deviation_from_target", group="sc_sc"),
            # Row 2 takeaways & variance
            Slot(id="bullets", widget="text", grid_area=(0, 5.6, 7.9, 1.9), max_chars=300, max_items=3, group="sc_blt"),
            Slot(id="var_check", widget="variance_graphic", grid_area=(8.2, 5.6, 3.8, 1.9),
                 data_pattern="deviation_from_target", group="sc_var"),
        ]
    ),
    "comparison_bars": Blueprint(
        archetype="comparison_bars",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0.1, 12, 0.7), max_chars=120),
            Slot(id="subtitle", widget="text", grid_area=(0, 0.8, 12, 0.4), max_chars=120),
            # Row 1 two comparison charts
            Slot(id="chart1", widget="chart_panel", grid_area=(0, 1.3, 5.8, 2.9),
                 data_pattern="comparison_rank", group="cb_ch1"),
            Slot(id="chart2", widget="chart_panel", grid_area=(6.2, 1.3, 5.8, 2.9),
                 data_pattern="comparison_pair", group="cb_ch2"),
            # Row 2 detailed table + KPI card (shifted up slightly to prevent footer collision)
            Slot(id="table", widget="table_panel", grid_area=(0, 4.3, 7.9, 3.2),
                 max_items=5, data_pattern="allocation_table", group="cb_tbl"),
            Slot(id="kpi_side", widget="kpi_card", grid_area=(8.2, 4.3, 3.8, 3.2),
                 max_chars=100, data_pattern="single_value", group="cb_k"),
        ]
    ),
    "variance_scorecard": Blueprint(
        archetype="variance_scorecard",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0.1, 12, 0.7), max_chars=120),
            Slot(id="subtitle", widget="text", grid_area=(0, 0.8, 12, 0.4), max_chars=120),
            # Row 1 Scorecard & Pie Chart (height expanded to 3.2 rows)
            Slot(id="scorecard", widget="scorecard", grid_area=(0, 1.3, 5.8, 3.2),
                 data_pattern="deviation_from_target", group="vs_sc"),
            Slot(id="pie_breakdown", widget="pie_chart", grid_area=(6.2, 1.3, 5.8, 3.2),
                 data_pattern="part_to_whole", group="vs_pie"),
            # Row 2 Two variance graphs
            Slot(id="var1", widget="variance_graphic", grid_area=(0, 4.7, 5.8, 2.8),
                 data_pattern="deviation_from_target", group="vs_v1"),
            Slot(id="var2", widget="variance_graphic", grid_area=(6.2, 4.7, 5.8, 2.8),
                 data_pattern="deviation_from_target", group="vs_v2"),
        ]
    ),
    "prioritization_matrix": Blueprint(
        archetype="prioritization_matrix",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0.1, 12, 0.7), max_chars=120),
            Slot(id="subtitle", widget="text", grid_area=(0, 0.8, 12, 0.4), max_chars=120),
            # Row 1 Matrix & Variance
            Slot(id="matrix", widget="matrix_view", grid_area=(0, 1.3, 7.9, 4.2),
                 data_pattern="prioritization_matrix", group="pm_mx"),
            Slot(id="var_side", widget="variance_graphic", grid_area=(8.2, 1.3, 3.8, 4.2),
                 data_pattern="deviation_from_target", group="pm_var"),
            # Row 2 Step milestones
            Slot(id="item1", widget="numbered_step", grid_area=(0, 5.7, 3.8, 1.8), max_chars=120, group="pm_i1"),
            Slot(id="item2", widget="numbered_step", grid_area=(4.1, 5.7, 3.8, 1.8), max_chars=120, group="pm_i2"),
            Slot(id="item3", widget="numbered_step", grid_area=(8.2, 5.7, 3.8, 1.8), max_chars=120, group="pm_i3"),
        ]
    ),
    "dashboard_with_table": Blueprint(
        archetype="dashboard_with_table",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0.1, 12, 0.7), max_chars=120),
            Slot(id="subtitle", widget="text", grid_area=(0, 0.8, 12, 0.4), max_chars=120),
            # Row 1 top KPIs
            Slot(id="kpi1", widget="stat_callout", grid_area=(0, 1.3, 3.8, 1.4),
                 max_chars=90, data_pattern="single_value", group="db_k1"),
            Slot(id="kpi2", widget="stat_callout", grid_area=(4.1, 1.3, 3.8, 1.4),
                 max_chars=90, data_pattern="single_value", group="db_k2"),
            Slot(id="kpi3", widget="stat_callout", grid_area=(8.2, 1.3, 3.8, 1.4),
                 max_chars=90, data_pattern="single_value", group="db_k3"),
            # Row 2 Chart & Table side-by-side
            Slot(id="chart", widget="chart_panel", grid_area=(0, 2.9, 5.8, 4.6),
                 data_pattern="trend", group="db_ch"),
            Slot(id="table", widget="table_panel", grid_area=(6.2, 2.9, 5.8, 4.6),
                 max_items=5, data_pattern="allocation_table", group="db_tbl"),
        ]
    ),
    "process_flow": Blueprint(
        archetype="process_flow",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0.1, 12, 0.7), max_chars=120),
            Slot(id="subtitle", widget="text", grid_area=(0, 0.8, 12, 0.4), max_chars=120),
            # Row 1 Process sequence
            Slot(id="chevron", widget="chevron_flow", grid_area=(0, 1.3, 12, 3.7),
                 data_pattern="process_sequence", group="pf_chv"),
            # Row 2 Two KPI pills & Text description
            Slot(id="kpi_left", widget="kpi_pill", grid_area=(0, 5.2, 3.8, 2.3),
                 max_chars=60, data_pattern="single_value", group="pf_kl"),
            Slot(id="kpi_right", widget="kpi_pill", grid_area=(4.1, 5.2, 3.8, 2.3),
                 max_chars=60, data_pattern="single_value", group="pf_kr"),
            Slot(id="insight", widget="text", grid_area=(8.2, 5.2, 3.8, 2.3),
                 max_chars=280, max_items=3, group="pf_ins"),
        ]
    ),
    "implementation_roadmap": Blueprint(
        archetype="implementation_roadmap",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0.1, 12, 0.7), max_chars=120),
            Slot(id="subtitle", widget="text", grid_area=(0, 0.8, 12, 0.4), max_chars=120),
            # Row 1 Gantt & bullets
            Slot(id="gantt", widget="gantt_strip", grid_area=(0, 1.3, 7.9, 4.2),
                 data_pattern="gantt_timeline", group="ir_gnt"),
            Slot(id="bullets", widget="text", grid_area=(8.2, 1.3, 3.8, 4.2), max_chars=400, max_items=5, group="ir_blt"),
            # Row 2 qualitative analysis
            Slot(id="insight", widget="text", grid_area=(0, 5.7, 7.9, 1.8), max_chars=180, group="ir_ins"),
            Slot(id="var_metric", widget="variance_graphic", grid_area=(8.2, 5.7, 3.8, 1.8),
                 data_pattern="deviation_from_target", group="ir_var"),
        ]
    ),
    "strategic_overlap": Blueprint(
        archetype="strategic_overlap",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0.1, 12, 0.7), max_chars=120),
            Slot(id="subtitle", widget="text", grid_area=(0, 0.8, 12, 0.4), max_chars=120),
            # Row 1 Venn & Two takeaways
            Slot(id="venn", widget="venn_diagram", grid_area=(0, 1.3, 6.5, 4.2),
                 data_pattern="overlap_analysis", group="so_vnn"),
            Slot(id="card1", widget="priority_card", grid_area=(6.8, 1.3, 5.2, 2.0), max_chars=160, group="so_c1"),
            Slot(id="card2", widget="priority_card", grid_area=(6.8, 3.5, 5.2, 2.0), max_chars=160, group="so_c2"),
            # Row 2 takeaway + Pie breakdown
            Slot(id="card3", widget="priority_card", grid_area=(0, 5.7, 5.8, 1.8), max_chars=160, group="so_c3"),
            Slot(id="pie_breakdown", widget="pie_chart", grid_area=(6.2, 5.7, 5.8, 1.8),
                 data_pattern="part_to_whole", group="so_pie"),
        ]
    ),
    "kpi_narrative": Blueprint(
        archetype="kpi_narrative",
        slots=[
            Slot(id="title", widget="text", grid_area=(0, 0.1, 12, 0.7), max_chars=120),
            Slot(id="subtitle", widget="text", grid_area=(0, 0.8, 12, 0.4), max_chars=120),
            # Row 1 Hero KPI & Bullet narrative
            Slot(id="hero_kpi", widget="kpi_card", grid_area=(0, 1.3, 3.8, 3.9),
                 max_chars=100, data_pattern="single_value", group="kn_hk"),
            Slot(id="bullets", widget="text", grid_area=(4.1, 1.3, 7.9, 3.9), max_chars=500, max_items=4, group="kn_blt"),
            # Row 2 Three horizontal stats
            Slot(id="stat1", widget="stat_callout", grid_area=(0, 5.4, 3.8, 2.1),
                 max_chars=90, data_pattern="single_value", group="kn_s1"),
            Slot(id="stat2", widget="stat_callout", grid_area=(4.1, 5.4, 3.8, 2.1),
                 max_chars=90, data_pattern="single_value", group="kn_s2"),
            Slot(id="stat3", widget="stat_callout", grid_area=(8.2, 5.4, 3.8, 2.1),
                 max_chars=90, data_pattern="single_value", group="kn_s3"),
        ]
    ),
}


def get_blueprint(archetype: str) -> Blueprint:
    """Retrieve the blueprint for a given archetype, raising ValueError if not found."""
    blueprint = ARCHETYPES.get(archetype.lower())
    if not blueprint:
        raise ValueError(f"Unknown archetype: {archetype}. Available: {list(ARCHETYPES.keys())}")
    return blueprint
