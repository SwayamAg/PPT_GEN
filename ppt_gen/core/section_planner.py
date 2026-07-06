from typing import List
from pydantic import BaseModel
from ppt_gen.core.llm_client import LLMClient
from ppt_gen.core.requirements_wizard import DeckRequirements
from ppt_gen.core.deck_templates import DeckPlan, SlideOutlineItem

class SectionPlannerOutput(BaseModel):
    slides: List[SlideOutlineItem]

class SectionPlanner:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def plan_sections(self, req: DeckRequirements, deck_plan: DeckPlan) -> SectionPlannerOutput:
        """Call LLM #2 to distribute slide counts and assign archetypes to slides."""
        system_prompt = (
            "You are a presentation design architect. Your task is to expand a high-level deck plan into slide outlines.\n"
            "You must distribute approximately the target slide count across the sections. For each slide, define:\n"
            "1. The section it belongs to (must match one of the section names exactly).\n"
            "2. A slide title (McKinsey-style, action-oriented, e.g., 'Core Margin Loss Driven by Pricing Pressures').\n"
            "3. The slide's purpose.\n"
            "4. A suggested archetype from this list: "
            "['title_challenge', 'two_column_initiative', 'stat_grid_charts', 'table_priorities', 'single_chart_focus', 'comparison_bars'].\n"
            "Match slide purposes to the appropriate archetypes:\n"
            " - 'title_challenge' for intro/problem statements\n"
            " - 'comparison_bars' for benchmarking against competitors\n"
            " - 'two_column_initiative' for comparing two workstreams or processes\n"
            " - 'single_chart_focus' for deep-diving into one trend\n"
            " - 'stat_grid_charts' for high-density dashboard KPIs and metrics\n"
            " - 'table_priorities' for next steps, budgets, and roadmaps\n"
            "Ensure the total slide count is close to the requested number of slides.\n"
            "Return JSON matching the schema."
        )

        sections_desc = "\n".join([f"- {s.name}: {s.purpose}" for s in deck_plan.sections])
        user_content = (
            f"Topic: {req.topic}\n"
            f"Deck Objective: {deck_plan.objective}\n"
            f"Sections:\n{sections_desc}\n"
            f"Target Slide Count: {req.slide_count}\n"
        )
        if req.extra_instructions:
            user_content += f"Extra Instructions: {req.extra_instructions}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        return self.llm_client.generate_structured(
            messages=messages,
            response_model=SectionPlannerOutput,
            temperature=self.llm_client.settings.llm.plan_temperature
        )
