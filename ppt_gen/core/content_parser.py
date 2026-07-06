from typing import List, Optional, Dict, Type, Any
from pydantic import BaseModel, create_model
from ppt_gen.core.blueprint_library import Blueprint

# Widget payload models
class TextPayload(BaseModel):
    text: str

class StatCalloutPayload(BaseModel):
    label: str
    value: Optional[str] = None

class KPIPillPayload(BaseModel):
    label: str
    value: Optional[str] = None

class NumberedStepPayload(BaseModel):
    badge: Optional[str] = None
    title: str
    desc: str

class PriorityCardPayload(BaseModel):
    badge: Optional[str] = None
    title: str
    desc: str

class ChartSeriesItem(BaseModel):
    name: str
    values: List[float]

class ChartDataPayload(BaseModel):
    labels: List[str]
    series: List[ChartSeriesItem]

class ChartPanelPayload(BaseModel):
    title: str
    chart_type: Optional[str] = None
    chart_data: Optional[ChartDataPayload] = None
    insight_caption: Optional[str] = None

class TablePanelPayload(BaseModel):
    title: str
    headers: Optional[List[str]] = None
    rows: Optional[List[List[str]]] = None
    insight_caption: Optional[str] = None

# Mapping widget name to its schema class
WIDGET_SCHEMAS = {
    "text": TextPayload,
    "stat_callout": StatCalloutPayload,
    "kpi_pill": KPIPillPayload,
    "numbered_step": NumberedStepPayload,
    "priority_card": PriorityCardPayload,
    "chart_panel": ChartPanelPayload,
    "table_panel": TablePanelPayload
}

def create_slide_payload_model(blueprint: Blueprint) -> Type[BaseModel]:
    """Dynamically generate a Pydantic model for a given blueprint's slots."""
    fields = {}
    for slot in blueprint.slots:
        schema_cls = WIDGET_SCHEMAS.get(slot.widget)
        if not schema_cls:
            raise ValueError(f"Unknown widget type {slot.widget} for slot {slot.id}")
        
        # All slot fields are required for the LLM to output
        fields[slot.id] = (schema_cls, ...)
        
    return create_model(f"{blueprint.archetype}_Payload", **fields)

class SlideContent(BaseModel):
    slide_index: int
    archetype: str
    slots: Dict[str, Any]  # slot_id -> payload dict
