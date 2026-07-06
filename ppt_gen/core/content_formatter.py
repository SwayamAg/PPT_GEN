from typing import Optional
from ppt_gen.core.blueprint_library import Blueprint
from ppt_gen.core.content_parser import SlideContent

def truncate_text(text: str, max_chars: Optional[int]) -> str:
    """Clamp string size using a smart ellipsis at a word boundary if possible."""
    if not text or not max_chars:
        return text
    if len(text) <= max_chars:
        return text
        
    truncated = text[:max_chars - 3]
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.7:  # If we have a space nearby, clip it cleanly
        return truncated[:last_space] + "..."
    return truncated + "..."

def format_content(slide_content: SlideContent, blueprint: Blueprint) -> SlideContent:
    """Rule-based text length and count clamping based on blueprint metadata."""
    formatted_slots = {}
    
    # Create mapping of slots by id
    slots_map = {slot.id: slot for slot in blueprint.slots}
    
    for slot_id, payload in slide_content.slots.items():
        slot = slots_map.get(slot_id)
        if not slot:
            formatted_slots[slot_id] = payload
            continue
            
        formatted_payload = dict(payload)
        
        # Format based on widget type
        if slot.widget == "text":
            if "text" in formatted_payload:
                formatted_payload["text"] = truncate_text(formatted_payload["text"], slot.max_chars)
                
        elif slot.widget in ("stat_callout", "kpi_pill"):
            if "label" in formatted_payload:
                formatted_payload["label"] = truncate_text(formatted_payload["label"], slot.max_chars)
                
        elif slot.widget in ("numbered_step", "priority_card"):
            if "title" in formatted_payload:
                formatted_payload["title"] = truncate_text(formatted_payload["title"], 60) # Default title length limit
            if "desc" in formatted_payload:
                formatted_payload["desc"] = truncate_text(formatted_payload["desc"], slot.max_chars)
                
        elif slot.widget == "chart_panel":
            if "title" in formatted_payload:
                formatted_payload["title"] = truncate_text(formatted_payload["title"], 80)
            if "insight_caption" in formatted_payload:
                formatted_payload["insight_caption"] = truncate_text(formatted_payload["insight_caption"], slot.max_chars or 100)
                
        elif slot.widget == "table_panel":
            if "title" in formatted_payload:
                formatted_payload["title"] = truncate_text(formatted_payload["title"], 80)
            if "insight_caption" in formatted_payload:
                formatted_payload["insight_caption"] = truncate_text(formatted_payload["insight_caption"], slot.max_chars or 100)
            
            # Clamp table rows
            if "rows" in formatted_payload and formatted_payload["rows"]:
                rows = formatted_payload["rows"]
                max_i = slot.max_items or 5
                if len(rows) > max_i:
                    # Truncate and add a final row "+N more items"
                    diff = len(rows) - max_i + 1
                    truncated_rows = rows[:max_i - 1]
                    cols_count = len(rows[0]) if rows else 2
                    fallback_row = [f"+{diff} more entries"] + [""] * (cols_count - 1)
                    formatted_payload["rows"] = truncated_rows + [fallback_row]
                    
        formatted_slots[slot_id] = formatted_payload
        
    return SlideContent(
        slide_index=slide_content.slide_index,
        archetype=slide_content.archetype,
        slots=formatted_slots
    )
