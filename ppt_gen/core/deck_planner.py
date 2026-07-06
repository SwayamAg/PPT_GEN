from ppt_gen.core.llm_client import LLMClient
from ppt_gen.core.requirements_wizard import DeckRequirements
from ppt_gen.core.deck_templates import DeckPlan

class DeckPlanner:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def plan_deck(self, req: DeckRequirements) -> DeckPlan:
        """Generate high-level strategic objectives and sections using the LLM."""
        system_prompt = (
            "You are a principal strategy consultant. Your task is to structure a high-level deck outline.\n"
            "Based on the provided topic, audience, and requirements, write a clear, professional presentation objective "
            "and divide the presentation into 3 to 5 logical sections.\n"
            "Each section must have a name and a clear description of its purpose.\n"
            "Avoid generic section names; make them specific to the topic.\n"
            "Do NOT output raw numbers. You must return your output strictly in JSON format matching the schema."
        )

        user_content = (
            f"Topic: {req.topic}\n"
            f"Audience: {req.audience}\n"
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
            response_model=DeckPlan,
            temperature=self.llm_client.settings.llm.plan_temperature
        )
