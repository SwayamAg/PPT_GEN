import json
import logging
import random
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, Any, Literal, Optional
from pydantic import BaseModel

from ppt_gen.core.deck_templates import SlideOutlineItem
from ppt_gen.core.blueprint_library import get_blueprint, Slot
from ppt_gen.core.content_parser import SlideContent
from ppt_gen.core.synthetic_data import SyntheticDataEngine, get_deterministic_seed
from ppt_gen.core.visual_selector import (
    resolve_slot_render_style,
    RENDER_STYLE_TO_CHART_TYPE,
    TIER_A_RENDER_STYLES,
)

if TYPE_CHECKING:
    from ppt_gen.core.llm_client import LLMClient

logger = logging.getLogger("plan_store")


# ---------------------------------------------------------------------------
# Caption Enrichment — response schema for LLM #4
# ---------------------------------------------------------------------------
class CaptionResponse(BaseModel):
    """Single rewritten insight caption returned by the enrichment LLM call."""
    caption: str


class ResolvedSlide(BaseModel):
    slide_index: int
    title: str
    archetype: str
    section: str
    slots: Dict[str, Any]


class FullDeckPlan(BaseModel):
    objective: str
    theme: Literal["light", "dark", "navy"] = "light"
    slides: List[ResolvedSlide]


def find_user_supplied_value(slot_id: str, label: str, user_data: Optional[Dict]) -> Any:
    """Fuzzy match user supplied data keys to slot IDs or slot labels."""
    if not user_data:
        return None
    # 1. Direct match by slot_id
    if slot_id in user_data:
        return user_data[slot_id]
        
    # 2. Match by clean label
    clean_label = str(label).lower().strip().replace("_", " ")
    for k, v in user_data.items():
        clean_k = str(k).lower().strip().replace("_", " ")
        if clean_k == clean_label or clean_k in clean_label or clean_label in clean_k:
            if len(clean_k) >= 3:  # Avoid matching tiny keys like 'id'
                return v
    return None


def compile_deck_plan(
    deck_id: str,
    objective: str,
    theme: Literal["light", "dark", "navy"],
    slides_outline: List[SlideOutlineItem],
    slides_content: List[SlideContent]
) -> FullDeckPlan:
    """Combine outlines, contents, and run the Synthetic Data Engine to resolve numbers.

    Visual type selection is now fully deterministic:
      1. SDE generates chart_data (so n_points / has_target signals are available)
      2. visual_selector.resolve_slot_render_style() picks render_style from data_pattern
      3. render_style is mapped to chart_type for Tier B widgets - LLM never touches this
    """
    engine = SyntheticDataEngine(deck_id=deck_id)
    resolved_slides = []

    # Map index to slide content for easy lookup
    content_map = {sc.slide_index: sc for sc in slides_content}

    for idx, outline in enumerate(slides_outline):
        content = content_map.get(idx)
        if not content:
            # Fallback if a slide generation failed
            content = SlideContent(slide_index=idx, archetype=outline.archetype, slots={})

        blueprint = get_blueprint(outline.archetype)
        resolved_slots = {}

        for slot in blueprint.slots:
            payload = content.slots.get(slot.id, {})
            # If payload is empty, initialize it according to widget type
            if not payload:
                if slot.widget == "text":
                    payload = {"text": f"Overview of {outline.slide_title}"}
                elif slot.widget in ("stat_callout", "kpi_card", "kpi_pill"):
                    payload = {"label": "Key metric performance", "value": "", "icon": None}
                elif slot.widget in ("numbered_step", "priority_card"):
                    payload = {"badge": "", "title": "Priority item", "desc": "Description", "icon": None}
                elif slot.widget in ("progress_indicator", "growth_arrow"):
                    payload = {"label": "Key growth metric", "value": "", "icon": None}
                elif slot.widget in ("benchmark_bar", "variance_graphic"):
                    payload = {"label": "Performance vs target", "value": "", "target": "", "icon": None}
                elif slot.widget == "market_share_strip":
                    payload = {"label": "Market share breakdown", "icon": None}
                elif slot.widget == "scorecard":
                    payload = {"label": "Performance scorecard", "icon": None}
                elif slot.widget == "matrix_view":
                    payload = {"label": "Prioritization matrix", "icon": None}
                elif slot.widget == "chart_panel":
                    payload = {"title": "Performance trend", "insight_caption": ""}
                elif slot.widget == "table_panel":
                    payload = {"title": "Project allocation", "insight_caption": ""}
                # Phase 2 extension: new widget fallback payloads
                elif slot.widget == "chevron_flow":
                    payload = {"steps": [
                        {"badge": "01", "title": "Assess",  "desc": "Baseline review",  "icon": "search"},
                        {"badge": "02", "title": "Design",  "desc": "Blueprint plans",   "icon": "lightbulb"},
                        {"badge": "03", "title": "Execute", "desc": "Rollout program",   "icon": "zap"},
                    ]}
                elif slot.widget == "gantt_strip":
                    payload = {
                        "label": "Roadmap",
                        "tasks": [],
                        "periods": ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"],
                    }
                elif slot.widget == "venn_diagram":
                    payload = {
                        "label": "Strategic Overlap",
                        "circles": [
                            {"name": "Capability A", "desc": "Core strength"},
                            {"name": "Capability B", "desc": "Market position"},
                        ],
                        "overlap_label": "Competitive Edge",
                    }
                elif slot.widget == "pie_chart":
                    payload = {
                        "label": "Share Breakdown",
                        "labels": ["Category A", "Category B", "Category C"],
                        "values": [45.0, 35.0, 20.0],
                    }

            # ----------------------------------------------------------------
            # Step 1: Run Synthetic Data Engine to resolve numeric values
            # ----------------------------------------------------------------
            resolved_chart_data = None

            if slot.data_pattern:
                if slot.widget in ("stat_callout", "kpi_card", "kpi_pill",
                                   "progress_indicator", "growth_arrow"):
                    label = payload.get("label", "")
                    user_val = find_user_supplied_value(slot.id, label, outline.user_data) if outline.user_data else None
                    if not user_val and payload.get("value") is not None and str(payload.get("value")).strip() != "":
                        user_val = payload.get("value")
                    resolved_val = engine.generate_slot_value(
                        idx, slot.id, label, slot.data_pattern, user_val
                    )
                    payload["value"] = resolved_val

                elif slot.widget in ("benchmark_bar", "variance_graphic"):
                    label = payload.get("label", "")
                    user_val = find_user_supplied_value(slot.id, label, outline.user_data) if outline.user_data else None
                    if not user_val and payload.get("value") is not None and str(payload.get("value")).strip() != "":
                        user_val = {
                            "actual_value": payload.get("value"),
                            "target_value": payload.get("target") or payload.get("value")
                        }
                    resolved_data = engine.generate_slot_value(
                        idx, slot.id, label, slot.data_pattern, user_val
                    )
                    if isinstance(resolved_data, dict):
                        payload["chart_data"] = resolved_data
                        resolved_chart_data = resolved_data
                        # Extract scalar actual/target for widget renderers
                        payload["actual_value"] = resolved_data.get("actual_value", 0)
                        payload["target_value"] = resolved_data.get("target_value", 0)

                elif slot.widget in ("scorecard", "matrix_view"):
                    label = payload.get("label", "")
                    user_val = find_user_supplied_value(slot.id, label, outline.user_data) if outline.user_data else None
                    if not user_val and payload.get("data") is not None:
                        user_val = payload.get("data")
                    resolved_data = engine.generate_slot_value(
                        idx, slot.id, label, slot.data_pattern, user_val
                    )
                    if isinstance(resolved_data, dict):
                        payload["data"] = resolved_data
                        resolved_chart_data = resolved_data

                elif slot.widget == "market_share_strip":
                    label = payload.get("label", "")
                    user_val = find_user_supplied_value(slot.id, label, outline.user_data) if outline.user_data else None
                    resolved_data = engine.generate_slot_value(
                        idx, slot.id, label, slot.data_pattern, user_val
                    )
                    if isinstance(resolved_data, dict):
                        payload["data"] = resolved_data
                        resolved_chart_data = resolved_data

                elif slot.widget == "chart_panel":
                    title = payload.get("title", "")
                    user_val = find_user_supplied_value(slot.id, title, outline.user_data) if outline.user_data else None
                    if not user_val and payload.get("chart_data") is not None:
                        cd = payload.get("chart_data")
                        if isinstance(cd, dict) and cd.get("series") and cd.get("labels"):
                            user_val = cd
                    resolved_chart = engine.generate_slot_value(
                        idx, slot.id, title, slot.data_pattern, user_val
                    )
                    if isinstance(resolved_chart, dict):
                        payload["chart_data"] = resolved_chart
                        resolved_chart_data = resolved_chart

                elif slot.widget == "table_panel":
                    title = payload.get("title", "")
                    user_val = find_user_supplied_value(slot.id, title, outline.user_data) if outline.user_data else None
                    if not user_val and payload.get("rows") is not None and payload.get("headers") is not None:
                        user_val = {
                            "headers": payload.get("headers"),
                            "values": payload.get("rows")
                        }
                    resolved_table = engine.generate_slot_value(
                        idx, slot.id, title, slot.data_pattern, user_val
                    )

                    # Merge LLM descriptive rows with synthetic numbers if available
                    llm_rows = payload.get("rows")
                    if llm_rows and resolved_table:
                        merged_rows = []
                        for r_idx, row in enumerate(llm_rows):
                            synth_row = resolved_table["values"][r_idx % len(resolved_table["values"])].copy()
                            if row:
                                synth_row[0] = row[0]
                            merged_rows.append(synth_row)
                        payload["rows"] = merged_rows
                        payload["headers"] = resolved_table["headers"]
                    elif resolved_table:
                        payload["headers"] = resolved_table["headers"]
                        payload["rows"] = resolved_table["values"]

                # Phase 2 extension: SDE calls for new widget types
                elif slot.widget == "gantt_strip":
                    label_val = payload.get("label", outline.slide_title)
                    user_val = find_user_supplied_value(slot.id, label_val, outline.user_data) if outline.user_data else None
                    if not user_val and payload.get("tasks") is not None:
                        user_val = {
                            "tasks": payload.get("tasks"),
                            "periods": payload.get("periods") or ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]
                        }
                    resolved_gantt = engine.generate_slot_value(
                        idx, slot.id, label_val, slot.data_pattern, user_val
                    )
                    if isinstance(resolved_gantt, dict):
                        payload.update(resolved_gantt)

                elif slot.widget == "venn_diagram":
                    label_val = payload.get("label", "")
                    user_val = find_user_supplied_value(slot.id, label_val, outline.user_data) if outline.user_data else None
                    if not user_val and payload.get("circles") is not None:
                        user_val = {
                            "circles": payload.get("circles"),
                            "overlap_label": payload.get("overlap_label")
                        }
                    resolved_venn = engine.generate_slot_value(
                        idx, slot.id, label_val, slot.data_pattern, user_val
                    )
                    if isinstance(resolved_venn, dict):
                        payload.update(resolved_venn)
                elif slot.widget == "pie_chart":
                    label_val = payload.get("label", "")
                    user_val = find_user_supplied_value(slot.id, label_val, outline.user_data) if outline.user_data else None
                    if not user_val and payload.get("values") is not None and payload.get("labels") is not None:
                        user_val = {
                            "labels": payload.get("labels"),
                            "series": [{"name": label_val, "values": payload.get("values")}]
                        }
                    resolved_pie = engine.generate_slot_value(
                        idx, slot.id, label_val, slot.data_pattern, user_val
                    )
                    if isinstance(resolved_pie, dict):
                        # Merge labels and values generated by part_to_whole SDE
                        payload["labels"] = resolved_pie.get("labels", [])
                        series_list = resolved_pie.get("series", [])
                        if series_list and isinstance(series_list, list):
                            payload["values"] = series_list[0].get("values", [])

                elif slot.widget == "chevron_flow":
                    label_val = payload.get("label", outline.slide_title)
                    user_val = find_user_supplied_value(slot.id, label_val, outline.user_data) if outline.user_data else None
                    if not user_val and payload.get("steps") is not None:
                        user_val = {
                            "steps": payload.get("steps")
                        }
                    resolved_steps = engine.generate_slot_value(
                        idx, slot.id, label_val, slot.data_pattern, user_val
                    )
                    if isinstance(resolved_steps, dict) and "steps" in resolved_steps:
                        payload.update(resolved_steps)

            # ----------------------------------------------------------------
            # Step 2: Visual Selector - resolve render_style deterministically
            # (never the LLM; uses seeded RNG freshly seeded per slot)
            # ----------------------------------------------------------------
            if slot.data_pattern and slot.widget not in ("text", "numbered_step",
                                                          "priority_card", "table_panel",
                                                           "chevron_flow", "gantt_strip",
                                                           "venn_diagram", "pie_chart"):
                slot_rng = random.Random(get_deterministic_seed(deck_id, idx, slot.id))
                render_style = resolve_slot_render_style(
                    slot_data_pattern=slot.data_pattern,
                    slot_render_style=slot.render_style,
                    resolved_chart_data=resolved_chart_data,
                    rng=slot_rng,
                )
                payload["render_style"] = render_style

                # For chart_panel slots: map render_style -> chart_type for Tier B rendering.
                # Only Tier B styles have entries in RENDER_STYLE_TO_CHART_TYPE.
                # If the selector picks a Tier A style, fall back to 'line' so the chart
                # engine produces something renderable until the Phase 2 widget dispatch
                # is wired (at which point chart_panel will be replaced by the Tier A widget).
                if slot.widget == "chart_panel" and render_style:
                    chart_type = RENDER_STYLE_TO_CHART_TYPE.get(render_style, "line")
                    payload["chart_type"] = chart_type

            resolved_slots[slot.id] = payload

        resolved_slides.append(ResolvedSlide(
            slide_index=idx,
            title=outline.slide_title,
            archetype=outline.archetype,
            section=outline.section,
            slots=resolved_slots
        ))

    return FullDeckPlan(
        objective=objective,
        theme=theme,
        slides=resolved_slides
    )


# ---------------------------------------------------------------------------
# LLM #4 — Data-Anchored Caption Enrichment
# ---------------------------------------------------------------------------
def enrich_captions_with_data(
    plan: FullDeckPlan,
    llm_client: "LLMClient",
    slides_outline: List[SlideOutlineItem],
) -> FullDeckPlan:
    """Rewrite insight_caption fields to reference actual resolved numeric values.

    Runs *after* compile_deck_plan() so real chart data and KPI values are
    already present in the plan.  Only chart_panel slots with both resolved
    chart_data AND a non-empty insight_caption are touched.  All other slots
    are left unchanged.

    Skipped entirely in mock mode to keep offline builds fast.
    Failures on individual slots are caught and logged — the original
    qualitative caption is preserved on any error.
    """
    if llm_client.mock_mode:
        logger.info("[caption_enrichment] Skipping — mock mode active.")
        return plan

    # Build a quick lookup: slide_index -> outline (for purpose/title context)
    outline_map: Dict[int, SlideOutlineItem] = {
        i: outline for i, outline in enumerate(slides_outline)
    }

    for slide in plan.slides:
        outline = outline_map.get(slide.slide_index)
        slide_purpose = outline.purpose if outline else ""
        slide_title = slide.title

        for slot_id, payload in slide.slots.items():
            # Only enrich chart_panel slots that have resolved chart_data
            # and a caption the LLM wrote earlier.
            if not isinstance(payload, dict):
                continue

            chart_data = payload.get("chart_data")
            current_caption = payload.get("insight_caption") or ""

            # Enrich any chart_panel slot that has resolved data,
            # whether the caption is null, empty, or already qualitative.
            if not chart_data:
                continue

            # Build a compact, readable summary of the resolved data
            labels = chart_data.get("labels", [])
            series = chart_data.get("series", [])

            series_lines = []
            for s in series:
                name = s.get("name", "?")
                values = s.get("values", [])
                series_lines.append(f'  "{name}": {values}')
            data_summary = "Labels: " + str(labels) + "\nSeries:\n" + "\n".join(series_lines)

            system_prompt = (
                "You are a slide insight copywriter. "
                "Rewrite the given caption to be data-anchored: "
                "reference specific numbers, differences, or trends visible in the data. "
                "1-2 sentences max. Professional, analytical, McKinsey-style. "
                "Do NOT invent numbers that are not in the data. "
                'Return JSON with a single key \"caption\".'
            )
            user_content = (
                f'Slide title: "{slide_title}"\n'
                f'Slide purpose: "{slide_purpose}"\n'
                f'Current caption: "{current_caption}"\n\n'
                f"Resolved chart data:\n{data_summary}"
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]

            try:
                logger.info(
                    f"[caption_enrichment] Enriching slide {slide.slide_index + 1} "
                    f"slot '{slot_id}'..."
                )
                result = llm_client.generate_structured(
                    messages=messages,
                    response_model=CaptionResponse,
                    temperature=0.3,
                )
                if result.caption:
                    payload["insight_caption"] = result.caption
                    logger.info(
                        f"[caption_enrichment] ✓ Updated '{slot_id}': {result.caption[:80]}…"
                    )
            except Exception as exc:
                logger.warning(
                    f"[caption_enrichment] Failed for slide {slide.slide_index + 1} "
                    f"slot '{slot_id}': {exc}. Keeping original caption."
                )

    return plan


def save_deck_plan(plan: FullDeckPlan, filepath: Path):
    """Write the full resolved deck plan to disk.

    Uses json.dumps instead of model_dump_json because Pydantic v2's
    model_dump_json with exclude_none=False does not recursively preserve
    icon keys inside Dict[str, Any] slot payloads.
    """
    filepath.parent.mkdir(exist_ok=True, parents=True)
    data = plan.model_dump(exclude_none=False, mode='json')
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2))


def load_deck_plan(filepath: Path) -> FullDeckPlan:
    """Read a resolved deck plan from disk."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return FullDeckPlan.model_validate(data)


def pregenerate_deck_data(
    deck_id: str,
    slides_outline: List[SlideOutlineItem]
) -> List[Dict[str, Any]]:
    """Generate all numeric, chart, and table values beforehand based on outline titles/purposes."""
    engine = SyntheticDataEngine(deck_id=deck_id)
    pregenerated_deck = []
    
    for idx, outline in enumerate(slides_outline):
        blueprint = get_blueprint(outline.archetype)
        slide_data = {}
        
        # Use slide title + purpose to infer overall trend direction
        slide_context_text = f"{outline.slide_title} {outline.purpose}"
        
        for slot in blueprint.slots:
            if slot.data_pattern:
                label_val = getattr(slot, 'label', slot.id)
                user_val = find_user_supplied_value(slot.id, label_val, outline.user_data) if outline.user_data else None
                resolved = engine.generate_slot_value(idx, slot.id, label_val, slot.data_pattern, user_val)
                
                # Format appropriately matching slot widget definitions
                if slot.widget in ("stat_callout", "kpi_pill", "kpi_card"):
                    slide_data[slot.id] = {"value": resolved}
                elif slot.widget == "chart_panel":
                    chart_type = "line"
                    if slot.data_pattern == "trend_series":
                        chart_type = "line"
                    elif slot.data_pattern == "paired_comparison":
                        chart_type = "grouped_bar"
                    elif slot.data_pattern == "ranked_bar":
                        chart_type = "bar"
                    slide_data[slot.id] = {
                        "chart_type": chart_type,
                        "chart_data": resolved
                    }
                elif slot.widget == "table_panel":
                    slide_data[slot.id] = {
                        "headers": resolved.get("headers") if resolved else [],
                        "rows": resolved.get("values") if resolved else []
                    }
            else:
                slide_data[slot.id] = {}
        pregenerated_deck.append(slide_data)
        
    return pregenerated_deck
