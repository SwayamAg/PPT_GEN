from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from ppt_gen.core.llm_client import LLMClient
from ppt_gen.core.deck_templates import SlideOutlineItem
from ppt_gen.core.blueprint_library import get_blueprint, Blueprint
from ppt_gen.core.content_parser import create_slide_payload_model, SlideContent

class SlideGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def generate_slide(
        self,
        slide_idx: int,
        item: SlideOutlineItem,
        prev_title: Optional[str] = None,
        next_title: Optional[str] = None
    ) -> SlideContent:
        """Call LLM #3 to fill in the text and structure slots for the slide archetype."""
        blueprint = get_blueprint(item.archetype)
        
        # Create a dynamic Pydantic model matching the slots for this blueprint
        payload_model = create_slide_payload_model(blueprint)
        
        system_prompt = (
            "You are an expert slide content copywriter. Your task is to fill the content slots for a single slide.\n"
            f"The slide archetype is '{item.archetype}'. You must generate a JSON object containing keys for every "
            "slot in the archetype blueprint. Do NOT add extra keys, and do NOT omit required keys.\n\n"
            "CRITICAL RULES:\n"
            "1. NEVER invent raw numeric values for KPI metrics or trends. Write only descriptive labels, titles, "
            "and captions. Keep the numeric fields (like 'value' in stat_callout or kpi_pill) as empty strings \"\" or null. "
            "A downstream engine will calculate correct numbers.\n"
            "2. If the user provided real numbers (below), you MUST use those values verbatim in the appropriate fields.\n"
            "3. Respect length constraints. Keep your language crisp, professional, and action-oriented (McKinsey-style).\n"
            "4. Return a JSON matching the requested schema exactly."
        )
        
        # Explain each slot's constraints in the user prompt
        slot_descriptions = []
        for slot in blueprint.slots:
            max_char_str = f"Max characters: {slot.max_chars}" if slot.max_chars else "No character limit"
            max_item_str = f"Max list items: {slot.max_items}" if slot.max_items else ""
            limits = f"({max_char_str}{', ' + max_item_str if max_item_str else ''})"
            slot_descriptions.append(
                f"- Slot ID '{slot.id}': widget type '{slot.widget}' {limits}. "
                f"Needs to represent content fitting the slide's purpose."
            )
        slots_text = "\n".join(slot_descriptions)
        
        user_content = (
            f"Slide Index: {slide_idx + 1}\n"
            f"Slide Title: {item.slide_title}\n"
            f"Slide Purpose: {item.purpose}\n"
            f"Section: {item.section}\n"
            f"Previous Slide Title: {prev_title or 'Start of Presentation'}\n"
            f"Next Slide Title: {next_title or 'End of Presentation'}\n\n"
            f"Slots to generate:\n{slots_text}\n"
        )
        
        # Inject user data if supplied
        if item.user_data:
            user_content += f"\nUser-supplied real numbers to include:\n{item.user_data}\n"
        else:
            user_content += "\nNo user-supplied numbers provided. Set values to empty strings.\n"
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        # Call LLM with the dynamically created validation model
        # The schema of payload_model is sent in the 'format' field to Ollama
        logger_name = "slide_generator"
        import logging
        logger = logging.getLogger(logger_name)
        logger.info(f"Generating slide {slide_idx + 1} with archetype {item.archetype}...")
        
        payload_response = self.llm_client.generate_structured(
            messages=messages,
            response_model=payload_model,
            temperature=self.llm_client.settings.llm.default_temperature
        )
        
        # Convert response model back to dictionary for storing in SlideContent
        slots_data = {}
        for key in payload_response.model_fields.keys():
            val = getattr(payload_response, key)
            if isinstance(val, BaseModel):
                slots_data[key] = val.model_dump()
            else:
                slots_data[key] = val
                
        return SlideContent(
            slide_index=slide_idx,
            archetype=item.archetype,
            slots=slots_data
        )
