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
        pregenerated_data: Dict[str, Any],
        prev_title: Optional[str] = None,
        next_title: Optional[str] = None
    ) -> SlideContent:
        """Call LLM #3 to fill in the text and structure slots for the slide archetype using pre-generated numbers."""
        blueprint = get_blueprint(item.archetype)
        
        # Create a dynamic Pydantic model matching the slots for this blueprint
        payload_model = create_slide_payload_model(blueprint)
        
        system_prompt = (
            "You are an expert slide content copywriter. Your task is to fill the content slots for a single slide.\n"
            f"The slide archetype is '{item.archetype}'. You must generate a JSON object containing keys for every "
            "slot in the archetype blueprint.\n\n"
            "CRITICAL RULES:\n"
            "1. You are provided with the exact pre-generated numeric data (KPI values, chart series, table contents) for this slide.\n"
            "2. DO NOT invent, alter, or falsify any numbers in your output. Only write descriptive labels, titles, "
            "and insight captions that narrate this dataset.\n"
            "3. Your insight captions, supporting text blocks, and bullet points must be highly specific, professional, and action-oriented (McKinsey-style). You must "
            "explicitly reference, analyze, and cite the specific values, percentages, or trends in the provided dataset to make "
            "the text align perfectly with what is visually shown on the charts, tables, or KPIs. For example, do not write generic advice in "
            "supporting bullet points next to a chart; instead, write data-driven analytical takeaways explaining the metrics, differences, or targets shown.\n"
            "4. Respect length constraints. Keep your language crisp.\n"
            "5. Return a JSON matching the requested schema exactly."
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
        
        # Format the pre-generated numeric data for the LLM to inspect
        pregen_formatted = []
        for slot_id, pregen_val in pregenerated_data.items():
            if not pregen_val:
                continue
            if "value" in pregen_val:
                pregen_formatted.append(f"- Slot '{slot_id}' (KPI/Stat) pre-generated value is: '{pregen_val['value']}'")
            elif "chart_data" in pregen_val and pregen_val["chart_data"]:
                pregen_formatted.append(f"- Slot '{slot_id}' (Chart) pre-generated dataset: {pregen_val['chart_data']}")
            elif "rows" in pregen_val and pregen_val["rows"]:
                pregen_formatted.append(
                    f"- Slot '{slot_id}' (Table) pre-generated columns: Headers: {pregen_val.get('headers')}, "
                    f"Rows: {pregen_val['rows']}"
                )
        pregen_text = "\n".join(pregen_formatted)
        
        user_content = (
            f"Slide Index: {slide_idx + 1}\n"
            f"Slide Title: {item.slide_title}\n"
            f"Slide Purpose: {item.purpose}\n"
            f"Section: {item.section}\n"
            f"Previous Slide Title: {prev_title or 'Start of Presentation'}\n"
            f"Next Slide Title: {next_title or 'End of Presentation'}\n\n"
            f"Archetype Slots:\n{slots_text}\n\n"
            f"PRE-GENERATED NUMERIC DATA FOR THIS SLIDE (Reference these exact numbers in your insight captions):\n"
            f"{pregen_text}\n"
        )
        
        # Inject user data if supplied
        if item.user_data:
            user_content += f"\nUser-supplied real numbers override: {item.user_data}\n"
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
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
