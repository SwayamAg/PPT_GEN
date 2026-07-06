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

def compile_deck_plan(
    deck_id: str,
    objective: str,
    theme: Literal["light", "dark"],
    slides_outline: List[SlideOutlineItem],
    slides_content: List[SlideContent]
) -> FullDeckPlan:
    """Combine outlines, contents, and run the Synthetic Data Engine to resolve numbers."""
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
        
        # Populate and merge synthetic/user data
        for slot in blueprint.slots:
            payload = content.slots.get(slot.id, {})
            # If payload is empty, initialize it according to widget type
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
            
            # Resolve synthetic values
            if slot.data_shape:
                if slot.widget in ("stat_callout", "kpi_pill"):
                    label = payload.get("label", "")
                    user_val = outline.user_data.get(slot.id) if outline.user_data else None
                    # Generate value
                    resolved_val = engine.generate_slot_value(idx, slot.id, label, slot.data_shape, user_val)
                    payload["value"] = resolved_val
                    
                elif slot.widget == "chart_panel":
                    title = payload.get("title", "")
                    user_val = outline.user_data.get(slot.id) if outline.user_data else None
                    resolved_chart = engine.generate_slot_value(idx, slot.id, title, slot.data_shape, user_val)
                    payload["chart_data"] = resolved_chart
                    # Infer chart type from data_shape if not set
                    if not payload.get("chart_type"):
                        if slot.data_shape == "trend_series":
                            payload["chart_type"] = "line"
                        elif slot.data_shape == "paired_comparison":
                            payload["chart_type"] = "grouped_bar"
                        elif slot.data_shape == "ranked_bar":
                            payload["chart_type"] = "bar"
                            
                elif slot.widget == "table_panel":
                    title = payload.get("title", "")
                    user_val = outline.user_data.get(slot.id) if outline.user_data else None
                    resolved_table = engine.generate_slot_value(idx, slot.id, title, slot.data_shape, user_val)
                    
                    # Merge LLM descriptive rows with synthetic numbers if available
                    llm_rows = payload.get("rows")
                    if llm_rows and resolved_table:
                        merged_rows = []
                        for r_idx, row in enumerate(llm_rows):
                            synth_row = resolved_table["values"][r_idx % len(resolved_table["values"])].copy()
                            if row:
                                synth_row[0] = row[0]  # Keep the LLM's text description for the row
                            merged_rows.append(synth_row)
                        payload["rows"] = merged_rows
                        payload["headers"] = resolved_table["headers"]
                    elif resolved_table:
                        payload["headers"] = resolved_table["headers"]
                        payload["rows"] = resolved_table["values"]
                        
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
