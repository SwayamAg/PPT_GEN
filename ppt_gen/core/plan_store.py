import json
from pathlib import Path
from typing import List, Dict, Any, Literal, Optional
from pydantic import BaseModel

from ppt_gen.core.deck_templates import SlideOutlineItem
from ppt_gen.core.blueprint_library import get_blueprint, Slot
from ppt_gen.core.content_parser import SlideContent
from ppt_gen.core.synthetic_data import SyntheticDataEngine

class ResolvedSlide(BaseModel):
    slide_index: int
    title: str
    archetype: str
    section: str
    slots: Dict[str, Any]

class FullDeckPlan(BaseModel):
    objective: str
    theme: Literal["light", "dark"] = "light"
    slides: List[ResolvedSlide]

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
            if slot.data_shape:
                user_val = outline.user_data.get(slot.id) if outline.user_data else None
                resolved = engine.generate_slot_value(idx, slot.id, slide_context_text, slot.data_shape, user_val)
                
                # Format appropriately matching slot widget definitions
                if slot.widget in ("stat_callout", "kpi_pill"):
                    slide_data[slot.id] = {"value": resolved}
                elif slot.widget == "chart_panel":
                    chart_type = "line"
                    if slot.data_shape == "trend_series":
                        chart_type = "line"
                    elif slot.data_shape == "paired_comparison":
                        chart_type = "grouped_bar"
                    elif slot.data_shape == "ranked_bar":
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

def compile_deck_plan(
    deck_id: str,
    objective: str,
    theme: Literal["light", "dark"],
    slides_outline: List[SlideOutlineItem],
    slides_content: List[SlideContent],
    pregenerated_deck: List[Dict[str, Any]]
) -> FullDeckPlan:
    """Merge the outlines, LLM-generated copy, and pre-generated data into a final FullDeckPlan."""
    resolved_slides = []
    
    # Map index to slide content for easy lookup
    content_map = {sc.slide_index: sc for sc in slides_content}
    
    for idx, outline in enumerate(slides_outline):
        content = content_map.get(idx)
        if not content:
            content = SlideContent(slide_index=idx, archetype=outline.archetype, slots={})
            
        blueprint = get_blueprint(outline.archetype)
        pregen_slide = pregenerated_deck[idx]
        resolved_slots = {}
        
        for slot in blueprint.slots:
            payload = content.slots.get(slot.id, {})
            # If payload is empty, initialize default mock texts
            if not payload:
                if slot.widget == "text":
                    payload = {"text": f"Overview of {outline.slide_title}"}
                elif slot.widget in ("stat_callout", "kpi_pill"):
                    payload = {"label": "Key metric performance", "value": ""}
                elif slot.widget in ("numbered_step", "priority_card"):
                    payload = {"badge": f"0{slot.id[-1]}" if slot.id[-1].isdigit() else "01", "title": "Priority item", "desc": "Description"}
                elif slot.widget == "chart_panel":
                    payload = {"title": "Performance trend", "insight_caption": ""}
                elif slot.widget == "table_panel":
                    payload = {"title": "Project allocation", "insight_caption": ""}
            
            # Merge pre-generated data fields
            pregen_val = pregen_slide.get(slot.id)
            if pregen_val:
                if slot.widget in ("stat_callout", "kpi_pill"):
                    payload["value"] = pregen_val.get("value", "")
                elif slot.widget == "chart_panel":
                    payload["chart_data"] = pregen_val.get("chart_data")
                    payload["chart_type"] = pregen_val.get("chart_type")
                elif slot.widget == "table_panel":
                    # Merge LLM descriptive table rows with pre-generated numbers
                    llm_rows = payload.get("rows")
                    pregen_rows = pregen_val.get("rows", [])
                    headers = pregen_val.get("headers", [])
                    
                    if llm_rows and pregen_rows:
                        merged_rows = []
                        for r_idx, row in enumerate(llm_rows):
                            synth_row = pregen_rows[r_idx % len(pregen_rows)].copy()
                            if row:
                                synth_row[0] = row[0]  # Overwrite first column description with LLM text
                            merged_rows.append(synth_row)
                        payload["rows"] = merged_rows
                        payload["headers"] = headers
                    else:
                        payload["rows"] = pregen_rows
                        payload["headers"] = headers
                        
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

def save_deck_plan(plan: FullDeckPlan, filepath: Path):
    """Write the full resolved deck plan to disk."""
    filepath.parent.mkdir(exist_ok=True, parents=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(plan.model_dump_json(indent=2))

def load_deck_plan(filepath: Path) -> FullDeckPlan:
    """Read a resolved deck plan from disk."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return FullDeckPlan.model_validate(data)
