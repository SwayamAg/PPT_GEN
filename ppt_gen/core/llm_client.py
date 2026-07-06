import json
import logging
from typing import Any, Dict, List, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from ppt_gen.core.settings import Settings

T = TypeVar("T", bound=BaseModel)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm_client")

class LLMClient:
    def __init__(self, settings: Settings, mock_mode: bool = False):
        self.settings = settings
        self.mock_mode = mock_mode
        self.host = settings.llm.host.rstrip("/")
        self.model = settings.llm.model
        self.max_retries = settings.llm.max_retries

    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: float = 0.3
    ) -> T:
        """Call Ollama chat API with JSON schema constraint and validation retries."""
        if self.mock_mode:
            return self._generate_mock(response_model)

        # Get JSON schema from Pydantic model
        schema = response_model.model_json_schema()
        
        # Build payload for Ollama
        # Pass the schema directly to 'format' for JSON grammar-constrained decoding in newer Ollama
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            },
            "format": schema
        }

        url = f"{self.host}/api/chat"
        client_messages = list(messages)  # Copy list to modify in retry loop

        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Calling Ollama ({self.model}) - Attempt {attempt + 1}")
                response = httpx.post(url, json=payload, timeout=60.0)
                
                if response.status_code != 200:
                    raise httpx.HTTPStatusError(
                        f"Ollama returned status code {response.status_code}: {response.text}",
                        request=response.request,
                        response=response
                    )
                
                result = response.json()
                content = result.get("message", {}).get("content", "")
                
                if not content:
                    raise ValueError("Ollama returned an empty response.")
                
                # Parse JSON content into Pydantic model
                parsed_data = json.loads(content)
                return response_model.model_validate(parsed_data)
                
            except (httpx.RequestError, httpx.HTTPStatusError, ValueError, json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Validation error or request failed on attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_retries:
                    logger.error("Reached maximum LLM retry attempts. Falling back to default construction.")
                    raise e
                
                # Setup repair loop prompt
                error_msg = f"Your previous response failed validation with error: {str(e)}. Please correct the JSON structure and keys to match the schema exactly."
                client_messages.append({"role": "assistant", "content": content if 'content' in locals() else ""})
                client_messages.append({"role": "user", "content": error_msg})
                payload["messages"] = client_messages

    def _generate_mock(self, response_model: Type[T]) -> T:
        """Generate static, plausible mock data for testing offline."""
        logger.info(f"Generating mock data for: {response_model.__name__}")
        
        model_name = response_model.__name__
        
        # We handle the specific model names we expect in the pipeline
        if "DeckPlan" in model_name:
            data = {
                "objective": "Establish a clear 3-year strategy to scale market penetration of the premium tier by 40% and recover core margins.",
                "sections": [
                    {"name": "Executive Summary", "purpose": "High-level summary of strategy, objectives, and core growth metrics."},
                    {"name": "Market & Competitive Benchmarking", "purpose": "Analyse our volume vs competitors and target growth segments."},
                    {"name": "Strategic Growth Initiatives", "purpose": "Detail key expansion plays and timeline of deployment."},
                    {"name": "Financial Plan & Next Steps", "purpose": "Projected revenue gains, resource allocation, and immediate roadmap items."}
                ]
            }
            return response_model.model_validate(data)
            
        elif "SectionPlannerOutput" in model_name or "slides" in response_model.model_fields:
            # Output of SectionPlanner (returns a list of SlideOutlineItem)
            data = {
                "slides": [
                    {
                        "section": "Executive Summary",
                        "slide_title": "Strategic Blueprint for Margin Recovery",
                        "purpose": "Show the problem statement, primary goal, and core KPI targets.",
                        "archetype": "title_challenge",
                        "data_mode": "synthetic",
                        "user_data": None
                    },
                    {
                        "section": "Market & Competitive Benchmarking",
                        "slide_title": "Market Penetration & Volume Benchmarks",
                        "purpose": "Compare our market volume growth against 3 main competitors.",
                        "archetype": "comparison_bars",
                        "data_mode": "synthetic",
                        "user_data": None
                    },
                    {
                        "section": "Strategic Growth Initiatives",
                        "slide_title": "Strategic Growth Plays & Workstreams",
                        "purpose": "Compare the two primary initiatives, their milestones, and conversion rate KPIs.",
                        "archetype": "two_column_initiative",
                        "data_mode": "synthetic",
                        "user_data": None
                    },
                    {
                        "section": "Strategic Growth Initiatives",
                        "slide_title": "Market Share Recovery Outlook",
                        "purpose": "Deep-dive projection showing our projected market share recovery over 6 quarters.",
                        "archetype": "single_chart_focus",
                        "data_mode": "synthetic",
                        "user_data": None
                    },
                    {
                        "section": "Financial Plan & Next Steps",
                        "slide_title": "Financial Gains Dashboard",
                        "purpose": "Provide a high-density summary of growth stat callouts and trend charts.",
                        "archetype": "stat_grid_charts",
                        "data_mode": "synthetic",
                        "user_data": None
                    },
                    {
                        "section": "Financial Plan & Next Steps",
                        "slide_title": "Resource Allocation & Priority Roadmap",
                        "purpose": "Show a next-steps roadmap table alongside prioritized resource allocations.",
                        "archetype": "table_priorities",
                        "data_mode": "synthetic",
                        "user_data": None
                    }
                ]
            }
            return response_model.model_validate(data)
            
        # For Slide Generation (dynamic models like title_challenge_Payload, etc.)
        # We construct mock values conforming to the sub-payload schemas (TextPayload, StatCalloutPayload, etc.)
        mock_dict = {}
        for field_name, field in response_model.model_fields.items():
            field_type = field.annotation
            field_type_name = getattr(field_type, "__name__", "")
            
            if "TextPayload" in field_type_name:
                # Provide custom content for standard fields if recognized, otherwise general mock
                if field_name == "challenge":
                    mock_dict[field_name] = {"text": "Margin erosion of 12% in the core tier due to aggressive competitor pricing and customer churn."}
                elif field_name == "title":
                    mock_dict[field_name] = {"text": "Strategic Blueprint for Margin Recovery"}
                elif "title" in field_name:
                    mock_dict[field_name] = {"text": f"Strategic Initiative for {field_name.replace('_', ' ').title()}"}
                elif field_name == "bullets":
                    mock_dict[field_name] = {"text": "Focusing on customer churn reduction.\nOptimizing pricing tier models.\nUpgrading partner sales networks.\nAutomating client onboarding workflows."}
                else:
                    mock_dict[field_name] = {"text": f"Mock text content for {field_name}."}
            elif "StatCalloutPayload" in field_type_name:
                mock_dict[field_name] = {"label": f"Growth in premium segments", "value": ""}
            elif "KPIPillPayload" in field_type_name:
                mock_dict[field_name] = {"label": f"Conversion rate indicator", "value": ""}
            elif "NumberedStepPayload" in field_type_name or "PriorityCardPayload" in field_type_name:
                # E.g. step1, card1
                mock_dict[field_name] = {
                    "badge": "01",
                    "title": f"Key Milestone Playbook {field_name}",
                    "desc": "Detailing action plan milestones and critical project execution steps."
                }
            elif "ChartPanelPayload" in field_type_name:
                mock_dict[field_name] = {
                    "title": f"Growth Trend Analysis ({field_name})",
                    "chart_type": None,
                    "chart_data": None,
                    "insight_caption": "Target Scenario projects a steady recovery over baseline."
                }
            elif "TablePanelPayload" in field_type_name:
                mock_dict[field_name] = {
                    "title": "Strategic Resource Allocations",
                    "headers": None,
                    "rows": [
                        ["Customer Retention Engine"],
                        ["Premium Tier Feature Expansion"],
                        ["Channel Partner Referral Program"],
                        ["Sales Team Direct Enablement"]
                    ],
                    "insight_caption": "Marketing and retention account for 68% of initial resource allocation."
                }
            else:
                mock_dict[field_name] = {}
                
        return response_model.model_validate(mock_dict)
