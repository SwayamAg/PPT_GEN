from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from ppt_gen.core.llm_client import LLMClient
from ppt_gen.core.deck_templates import SlideOutlineItem
from ppt_gen.core.blueprint_library import get_blueprint, Blueprint
from ppt_gen.core.content_parser import create_slide_payload_model, SlideContent
from ppt_gen.core.icon_library import icon_enum_for_prompt

class SlideGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def generate_slide(
        self,
        slide_idx: int,
        item: SlideOutlineItem,
        prev_title: Optional[str] = None,
        next_title: Optional[str] = None,
        deck_objective: Optional[str] = None,
        all_slide_titles: Optional[List[str]] = None,
        previous_slides_content: Optional[List[SlideContent]] = None,
        extra_instructions: Optional[str] = None,
    ) -> SlideContent:
        """Call LLM #3 to fill in the text and structure slots for the slide archetype."""
        blueprint = get_blueprint(item.archetype)
        
        # Create a dynamic Pydantic model matching the slots for this blueprint
        payload_model = create_slide_payload_model(blueprint)

        # Build narrative context string
        narrative_parts = []
        if deck_objective:
            narrative_parts.append(f"Overall deck objective: {deck_objective}")
        if all_slide_titles:
            titles_str = "\n".join(
                f"  {'→ [THIS SLIDE]' if i == slide_idx else f'  [{i+1}]'} {t}"
                for i, t in enumerate(all_slide_titles)
            )
            narrative_parts.append(f"Full deck narrative flow:\n{titles_str}")
            
        if previous_slides_content and all_slide_titles:
            prev_summaries = []
            for prev in previous_slides_content:
                s_idx = prev.slide_index
                s_title = all_slide_titles[s_idx] if s_idx < len(all_slide_titles) else f"Slide {s_idx+1}"
                details = []
                for s_id, pay in prev.slots.items():
                    if isinstance(pay, dict):
                        for f in ("title", "text", "desc", "label"):
                            val = pay.get(f)
                            if val and isinstance(val, str) and len(val.strip()) > 8:
                                details.append(f"{s_id}: {val.strip()[:60]}")
                if details:
                    prev_summaries.append(f"Slide {s_idx+1} ('{s_title}'): {'; '.join(details[:3])}")
            if prev_summaries:
                narrative_parts.append("Insights and content already generated in previous slides (DO NOT REPEAT these points, concepts, or terminology):\n" + "\n".join(prev_summaries))

        narrative_context = "\n".join(narrative_parts)

        # Archetype-specific guidance
        archetype_guidance = {
            "executive_cover":       "Hero cover — write a commanding title and a crisp 1-sentence subtitle that sets the deck's strategic stakes.",
            "closing_takeaways":     "Closing summary — each takeaway card should distil ONE clear action or conclusion. No repetition across cards.",
            "title_challenge":       "Problem framing — the 'challenge' text block should clearly articulate the core business problem; the 'action' step should be a single key recommended initiative.",
            "two_column_initiative": "Two-column initiative — left column and right column must cover DIFFERENT workstreams. bullets1/bullets2 should list 2-3 distinct insight points each.",
            "stat_grid_charts":      "Stat grid — each KPI card label must be distinct, non-repetitive. The takeaway cards in row 3 must offer fresh insight, not restate the KPI labels.",
            "table_priorities":      "Table + steps — the table rows should be specific named initiatives or line items. The 3 step cards should each map to a different next action.",
            "single_chart_focus":    "Chart focus — bullets should provide 2-3 analytical observations about the chart trend. var_check should reference the same metric as the chart.",
            "comparison_bars":       "Comparison — chart1 and chart2 must compare DIFFERENT dimensions or entities. Table rows should add detail not visible in the charts.",
            "variance_scorecard":    "Variance + pie — scorecard rows and variance graphics should reference the same KPI domain. Pie chart label should name the breakdown category.",
            "prioritization_matrix": "Matrix — the three numbered items below the matrix should correspond to the top-3 priority quadrant items in the matrix.",
            "dashboard_with_table":  "Dashboard — chart and table should cover the same topic from different angles (trend vs breakdown). KPIs should be the headline metrics.",
            "process_flow":          "Process — chevron steps must be sequential (Assess → Design → Execute style). The insight text should summarise the end-state outcome.",
            "implementation_roadmap":"Roadmap — Gantt tasks should have distinct phase names. Bullets should list key milestones. Insight should state the overall timeline.",
            "strategic_overlap":     "Venn — each circle represents a distinct strategic capability. The overlap label names the resulting competitive advantage. Priority cards add context.",
            "kpi_narrative":         "KPI narrative — hero_kpi should be the single most important metric. Bullet points elaborate on why this number matters. Stat cards are supporting metrics.",
        }
        arch_hint = archetype_guidance.get(item.archetype, "")

        system_prompt = (
            "You are an expert McKinsey-style slide content copywriter generating content for a professional business presentation.\n"
            f"The slide archetype is '{item.archetype}'. You must generate a JSON object containing keys for every "
            "slot in the archetype blueprint. Do NOT add extra keys, and do NOT omit required keys.\n\n"
            "CRITICAL RULES:\n"
            "1. Use your knowledge of the presentation topic to generate highly realistic, plausible, and "
            "domain-relevant numeric values, trends, percentages, and targets for all numeric fields, chart series, "
            "and table rows. Avoid generic placeholders or empty values unless no meaningful numbers are possible.\n"
            "2. If the user provided real numbers verbatim (below), prioritize and use those values in the appropriate fields.\n"
            "3. Respect the CHARACTER LIMIT for each slot exactly — do not exceed it. Write concise, action-oriented copy.\n"
            "4. CONTENT COHERENCE: This slide is part of a larger narrative. Do NOT repeat content from other slides. "
            "Each slide must advance the story.\n"
            "5. Do NOT use generic filler like 'Key Metric' or 'Description here'. Write specific, domain-relevant copy.\n"
            "6. For slots that include an 'icon' field, pick ONE icon name from this enum that best matches the "
            f"slot's meaning (or null if none fits): {icon_enum_for_prompt()}.\n"
            "7. badge fields: only set a badge if it is a meaningful short label (e.g. 'Phase 1', 'Priority'). "
            "If not meaningful, leave badge as empty string \"\".\n"
            "8. CRITICAL: All plain string fields (title, label, desc, text, value, insight_caption etc.) MUST be "
            "plain JSON strings — NOT objects or dicts. WRONG: {\"title\": {\"text\": \"...\"}}. RIGHT: {\"title\": \"...\"}.\n\n"
            f"ARCHETYPE GUIDANCE: {arch_hint}"
        )
        
        # Explain each slot's constraints in the user prompt
        slot_descriptions = []
        for slot in blueprint.slots:
            max_char_str = f"Max {slot.max_chars} chars" if slot.max_chars else "No char limit"
            max_item_str = f", max {slot.max_items} items" if slot.max_items else ""
            slot_descriptions.append(
                f"- '{slot.id}' ({slot.widget}): {max_char_str}{max_item_str}."
            )
        slots_text = "\n".join(slot_descriptions)
        
        user_content = (
            f"Slide {slide_idx + 1} of {len(all_slide_titles) if all_slide_titles else '?'}\n"
            f"Slide Title: {item.slide_title}\n"
            f"Slide Purpose: {item.purpose}\n"
            f"Section: {item.section}\n"
            f"Previous slide: {prev_title or 'Start of Presentation'}\n"
            f"Next slide: {next_title or 'End of Presentation'}\n\n"
            f"Deck context:\n{narrative_context}\n\n"
            f"Slots to fill (respect character limits):\n{slots_text}\n"
        )
        
        # Inject user data if supplied
        if item.user_data:
            user_content += f"\nUser-supplied real numbers to include verbatim:\n{item.user_data}\n"
        else:
            user_content += "\nNo user-supplied numbers provided. Generate realistic and plausible numbers based on your domain knowledge of the topic.\n"
            
        if extra_instructions:
            user_content += f"\nAdditional narrative instructions/tone guidelines to follow:\n{extra_instructions}\n"
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        import logging
        logger = logging.getLogger("slide_generator")
        logger.info(f"Generating slide {slide_idx + 1} with archetype {item.archetype}...")
        
        payload_response = self.llm_client.generate_structured(
            messages=messages,
            response_model=payload_model,
            temperature=self.llm_client.settings.llm.default_temperature
        )
        
        slots_data = {}
        for key in type(payload_response).model_fields.keys():
            val = getattr(payload_response, key)
            if isinstance(val, BaseModel):
                slots_data[key] = val.model_dump(exclude_none=False)
            else:
                slots_data[key] = val
                
        return SlideContent(
            slide_index=slide_idx,
            archetype=item.archetype,
            slots=slots_data
        )

