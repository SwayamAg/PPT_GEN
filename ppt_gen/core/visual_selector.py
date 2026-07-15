"""
visual_selector.py — §6.1 of the architecture spec.

Resolves each numeric slot's render_style from its archetype-declared
data_pattern via a deterministic rule-based function.  The LLM is never
involved in this decision.

ELIGIBLE_RENDER_STYLES maps each data_pattern to an ordered list of
eligible render styles.  The first entry is the "safe default" used when
the pattern has only one eligible style or when deterministic rules select
it (e.g. n_points == 1).  For patterns with multiple eligible styles,
select_render_style() picks between them using the caller's seeded RNG,
which guarantees:
  • determinism per deck (same seed → same pick every re-render)
  • variety across decks (different seed → different pick)
"""

from random import Random
from typing import Optional

ELIGIBLE_RENDER_STYLES: dict[str, list[str]] = {
    # ── Tier A ────────────────────────────────────────────────────────────
    "single_value":          ["stat_callout", "kpi_card", "growth_arrow"],
    "comparison_pair":       ["paired_comparison_bar", "benchmark_bar", "growth_arrow"],
    "comparison_rank":       ["ranked_bar", "market_share_strip"],
    "trend":                 ["trend_line", "growth_arrow"],   # growth_arrow when n_points <= 2
    "part_to_whole":         ["pie_chart", "market_share_strip"],           # pie reserved for later
    "deviation_from_target": ["variance_graphic", "benchmark_bar"],
    "allocation_table":      ["table_panel"],
    "prioritization_matrix": ["matrix_view"],
    # Phase 2 extension patterns
    "gantt_timeline":        ["gantt_strip"],
    "overlap_analysis":      ["venn_diagram"],
    "process_sequence":      ["chevron_flow"],

    # ── Tier B ────────────────────────────────────────────────────────────
    "cumulative_buildup":    ["waterfall"],
    "distribution_grid":     ["heatmap"],
}

# Mapping from a render_style token to the chart_engine chart_type string
# (only for Tier B styles that go through chart_engine; Tier A styles are
# rendered by business_widgets.py and do not use this mapping).
RENDER_STYLE_TO_CHART_TYPE: dict[str, str] = {
    "ranked_bar":            "bar",
    "paired_comparison_bar": "grouped_bar",
    "trend_line":            "line",
    "multi_bar":             "multi_bar",
    "waterfall":             "waterfall",
    "heatmap":               "heatmap",
}

# Tier A render styles that are handled by business_widgets.py (shape-based)
TIER_A_RENDER_STYLES: set[str] = {
    "stat_callout",
    "kpi_card",
    "growth_arrow",
    "benchmark_bar",
    "market_share_strip",
    "variance_graphic",
    "matrix_view",
    "table_panel",
    "gantt_strip",
    "venn_diagram",
    "chevron_flow",
    "pie_chart",
}


def select_render_style(
    pattern: str,
    n_points: int,
    has_target: bool,
    rng: Random,
) -> str:
    """
    Deterministically pick a render_style for the given data_pattern.

    Rules (per §6.1):
      • "trend"            with n_points <= 2  → always "growth_arrow"
      • "comparison_pair"  with has_target     → always "benchmark_bar"
      • single-option patterns                 → return that option
      • all others                             → rng.choice(eligible list)

    Parameters
    ----------
    pattern   : the data_pattern declared by the archetype Slot
    n_points  : number of data labels / time periods in the resolved data
    has_target: True if the resolved data includes a target / benchmark series
    rng       : a pre-seeded Random instance (seed = hash(deck_id, slide_id, slot_id))

    Returns
    -------
    A render_style string from ELIGIBLE_RENDER_STYLES[pattern].
    """
    options = ELIGIBLE_RENDER_STYLES.get(pattern)
    if not options:
        # Unknown pattern — fall back to stat_callout, a safe no-op widget
        return "stat_callout"

    # Deterministic priority rules
    if pattern == "trend" and n_points <= 2:
        return "growth_arrow"

    if pattern == "comparison_pair" and has_target:
        return "benchmark_bar"

    # Single-option patterns need no randomness
    if len(options) == 1:
        return options[0]

    # Multi-option: use seeded RNG for variety across decks
    return rng.choice(options)


def resolve_slot_render_style(
    slot_data_pattern: Optional[str],
    slot_render_style: Optional[str],
    resolved_chart_data: Optional[dict],
    rng: Random,
) -> Optional[str]:
    """
    Convenience wrapper used by plan_store.compile_deck_plan().

    If the slot already pins a render_style (archetype set it explicitly),
    return it as-is.  Otherwise call select_render_style() with signals
    derived from the resolved chart data.
    """
    if slot_render_style is not None:
        return slot_render_style

    if slot_data_pattern is None:
        return None

    # Derive signals from resolved chart data
    n_points = 1
    has_target = False

    if resolved_chart_data and isinstance(resolved_chart_data, dict):
        labels = resolved_chart_data.get("labels", [])
        series = resolved_chart_data.get("series", [])
        n_points = len(labels) if labels else 1

        # has_target: any series whose name contains "target" or "benchmark"
        for s in series:
            name_lower = (s.get("name") or "").lower()
            if "target" in name_lower or "benchmark" in name_lower:
                has_target = True
                break

    return select_render_style(slot_data_pattern, n_points, has_target, rng)
