from typing import List, Optional, Dict, Type, Any
from pydantic import BaseModel, create_model, field_validator, model_validator
from ppt_gen.core.blueprint_library import Blueprint


def _coerce_str(v: Any) -> str:
    """Auto-unwrap LLM-produced dicts like {'text': '...'} to plain strings."""
    if isinstance(v, dict):
        for key in ("text", "title", "label", "value", "desc", "name", "content"):
            if key in v and isinstance(v[key], str):
                return v[key]
        # last resort: stringify the dict
        return str(v)
    return str(v) if v is not None else ""


def _coerce_payload(data: Any, primary_key: str) -> Any:
    """Auto-wrap a plain string into a payload dict.

    If the LLM returns a raw string for a slot that expects a dict/model,
    wrap it: 'Dual-Track Growth' -> {'text': 'Dual-Track Growth'}.
    This is the inverse of _coerce_str and fixes the mirror-image LLM error.
    """
    if isinstance(data, str):
        return {primary_key: data}
    return data

# ---------------------------------------------------------------------------
# Widget payload models
# ---------------------------------------------------------------------------
class TextPayload(BaseModel):
    text: str

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "text")

    @field_validator("text", mode="before")
    @classmethod
    def coerce_text(cls, v): return _coerce_str(v)

class StatCalloutPayload(BaseModel):
    label: str
    value: Optional[str] = None
    icon: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "label")

    @field_validator("label", "value", "icon", mode="before")
    @classmethod
    def coerce_fields(cls, v): return _coerce_str(v) if v is not None else v

class KPICardPayload(BaseModel):
    label: str
    value: Optional[str] = None
    icon: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "label")

    @field_validator("label", "value", "icon", mode="before")
    @classmethod
    def coerce_fields(cls, v): return _coerce_str(v) if v is not None else v

class KPIPillPayload(BaseModel):
    label: str
    value: Optional[str] = None
    icon: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "label")

    @field_validator("label", "value", "icon", mode="before")
    @classmethod
    def coerce_fields(cls, v): return _coerce_str(v) if v is not None else v

class NumberedStepPayload(BaseModel):
    badge: Optional[str] = None
    title: str
    desc: str
    icon: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "title")

    @field_validator("badge", "title", "desc", "icon", mode="before")
    @classmethod
    def coerce_fields(cls, v): return _coerce_str(v) if v is not None else v

class PriorityCardPayload(BaseModel):
    badge: Optional[str] = None
    title: str
    desc: str
    icon: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "title")

    @field_validator("badge", "title", "desc", "icon", mode="before")
    @classmethod
    def coerce_fields(cls, v): return _coerce_str(v) if v is not None else v

class ProgressIndicatorPayload(BaseModel):
    label: str
    value: Optional[str] = None
    icon: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "label")

class GrowthArrowPayload(BaseModel):
    label: str
    value: Optional[str] = None
    icon: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "label")

class BenchmarkBarPayload(BaseModel):
    label: str
    value: Optional[str] = None
    target: Optional[str] = None
    icon: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "label")

class MarketShareStripPayload(BaseModel):
    label: str
    icon: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "label")

class ScorecardPayload(BaseModel):
    label: str
    icon: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "label")

class MatrixViewPayload(BaseModel):
    label: str
    icon: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "label")

class VarianceGraphicPayload(BaseModel):
    label: str
    value: Optional[str] = None
    target: Optional[str] = None
    icon: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "label")

class EyebrowPayload(BaseModel):
    """Uppercase letter-spaced label above a section header (gold in navy theme)."""
    text: str

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "text")

class FooterPayload(BaseModel):
    """Muted footer line at bottom of title/closing slides."""
    text: str

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "text")

# ---------------------------------------------------------------------------
# Phase 2 extension: new visual widget payload models
# ---------------------------------------------------------------------------
class ChevronStepItem(BaseModel):
    badge: str
    title: str
    desc: str
    icon: Optional[str] = None

class ChevronFlowPayload(BaseModel):
    """Horizontal chevron process-flow strip with 3–5 steps."""
    steps: List[ChevronStepItem]

class GanttTaskItem(BaseModel):
    name: str
    start: int  # 0-indexed period
    end: int    # exclusive end period
    color: Optional[str] = None  # e.g. "accent_primary"

class GanttStripPayload(BaseModel):
    """Horizontal Gantt chart with named tasks across time periods."""
    label: str
    tasks: List[GanttTaskItem]
    periods: Optional[List[str]] = None

class VennCircleItem(BaseModel):
    name: str
    desc: Optional[str] = None

class VennDiagramPayload(BaseModel):
    """2-circle or 3-circle Venn diagram with an overlap label."""
    label: str
    circles: List[VennCircleItem]
    overlap_label: Optional[str] = None

class ChartSeriesItem(BaseModel):
    name: str
    values: List[float]

class ChartDataPayload(BaseModel):
    labels: List[str]
    series: List[ChartSeriesItem]

class ChartPanelPayload(BaseModel):
    title: str
    # chart_type is intentionally NOT here — it is resolved by the Visual Selector
    # (visual_selector.py) in plan_store.compile_deck_plan(), never by the LLM.
    chart_data: Optional[ChartDataPayload] = None
    insight_caption: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def coerce_from_str(cls, v): return _coerce_payload(v, "title")

    @field_validator("title", "insight_caption", mode="before")
    @classmethod
    def coerce_fields(cls, v): return _coerce_str(v) if v is not None else v

class TablePanelPayload(BaseModel):
    title: str
    headers: Optional[List[str]] = None
    rows: Optional[List[List[str]]] = None
    insight_caption: Optional[str] = None

    @field_validator("title", "insight_caption", mode="before")
    @classmethod
    def coerce_fields(cls, v): return _coerce_str(v) if v is not None else v

# Mapping widget name → its schema class

class PieChartPayload(BaseModel):
    """Pie chart / doughnut breakdown with label and values."""
    label: str
    labels: List[str]
    values: List[float]
    icon: Optional[str] = None

WIDGET_SCHEMAS: Dict[str, Type[BaseModel]] = {
    "text":               TextPayload,
    "stat_callout":       StatCalloutPayload,
    "kpi_card":           KPICardPayload,
    "kpi_pill":           KPIPillPayload,
    "numbered_step":      NumberedStepPayload,
    "priority_card":      PriorityCardPayload,
    "progress_indicator": ProgressIndicatorPayload,
    "growth_arrow":       GrowthArrowPayload,
    "benchmark_bar":      BenchmarkBarPayload,
    "market_share_strip": MarketShareStripPayload,
    "scorecard":          ScorecardPayload,
    "matrix_view":        MatrixViewPayload,
    "variance_graphic":   VarianceGraphicPayload,
    "chart_panel":        ChartPanelPayload,
    "table_panel":        TablePanelPayload,
    # Phase C: new widgets
    "eyebrow":            EyebrowPayload,
    "footer":             FooterPayload,
    # icon_text_row is used in archetypes but treated as text for LLM purposes
    "icon_text_row":      TextPayload,
    # Phase 2 extension: new visual widgets
    "chevron_flow":       ChevronFlowPayload,
    "gantt_strip":        GanttStripPayload,
    "venn_diagram":       VennDiagramPayload,
    "pie_chart":          PieChartPayload,
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
