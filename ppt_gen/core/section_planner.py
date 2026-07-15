from typing import List
from pydantic import BaseModel
from ppt_gen.core.llm_client import LLMClient
from ppt_gen.core.requirements_wizard import DeckRequirements
from ppt_gen.core.deck_templates import DeckPlan, SlideOutlineItem, CustomizedPresetOutput

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
            "4. A suggested archetype from this list (ALL 15 are valid):\n"
            "['executive_cover', 'closing_takeaways', 'title_challenge', 'two_column_initiative',\n"
            " 'stat_grid_charts', 'table_priorities', 'single_chart_focus', 'comparison_bars',\n"
            " 'variance_scorecard', 'prioritization_matrix', 'dashboard_with_table', 'process_flow',\n"
            " 'implementation_roadmap', 'strategic_overlap', 'kpi_narrative']\n"
            "Match slide purposes to the most fitting archetype:\n"
            " - 'executive_cover'        → opening hero/cover slide (use ONCE at the very start)\n"
            " - 'closing_takeaways'      → final summary of key recommendations (use ONCE at the end)\n"
            " - 'title_challenge'        → intro, problem statement, challenge framing with KPIs\n"
            " - 'comparison_bars'        → side-by-side benchmarking of two or more entities\n"
            " - 'two_column_initiative'  → comparing two workstreams, initiatives, or processes\n"
            " - 'single_chart_focus'     → deep-dive on one trend with a large prominent chart\n"
            " - 'stat_grid_charts'       → high-density KPI + chart dashboard (3+ KPIs + 2 charts)\n"
            " - 'dashboard_with_table'   → KPI row + side-by-side chart and data table\n"
            " - 'table_priorities'       → next-steps roadmap, budget allocation, or resource table\n"
            " - 'variance_scorecard'     → actual vs target variance analysis with scorecard and pie chart\n"
            " - 'prioritization_matrix'  → effort-vs-impact 2x2 matrix for initiative prioritization\n"
            " - 'process_flow'           → step-by-step chevron process diagram with KPIs\n"
            " - 'implementation_roadmap' → Gantt timeline / phased roadmap with milestone bullets\n"
            " - 'strategic_overlap'      → Venn diagram showing strategic overlap between capabilities\n"
            " - 'kpi_narrative'          → hero KPI + narrative bullet points + supporting stats\n"
            "Always start with 'executive_cover' and end with 'closing_takeaways' when slide count allows.\n"
            "Ensure the total slide count is close to the requested number.\n"
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

    def customize_preset(self, req: DeckRequirements, preset: dict) -> CustomizedPresetOutput:
        """Call LLM to customize the slide titles and purposes of a preset outline based on the presentation topic."""
        import json
        system_prompt = (
            "You are a principal strategy consultant and presentation architect.\n"
            "Your task is to customize a pre-structured presentation template for a specific presentation topic and audience.\n"
            "You will be given the target topic, audience, and the static template's objective, sections, and slide outlines.\n"
            "You must rewrite the objective, section names/purposes, and slide titles/purposes to be highly specific, "
            "McKinsey-style, action-oriented, and directly relevant to the user's presentation topic and audience.\n\n"
            "CRITICAL RULES:\n"
            "1. Do NOT change the number of slides or their suggested archetypes. Keep the sequence of archetypes exactly as provided.\n"
            "2. Ensure slide section names match your customized section names exactly.\n"
            "3. Slide titles must be action-oriented and customized to the topic.\n"
            "4. Return your output strictly in JSON format matching the schema."
        )

        user_content = (
            f"Target Topic: {req.topic}\n"
            f"Target Audience: {req.audience}\n"
            f"Static Preset Template Structure:\n"
            f"Objective: {preset['objective']}\n"
            f"Sections:\n{json.dumps(preset['sections'], indent=2)}\n"
            f"Slides:\n{json.dumps(preset['slides'], indent=2)}\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        return self.llm_client.generate_structured(
            messages=messages,
            response_model=CustomizedPresetOutput,
            temperature=self.llm_client.settings.llm.plan_temperature
        )
