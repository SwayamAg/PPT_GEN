from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt

console = Console()

class DeckRequirements(BaseModel):
    topic: str
    audience: str
    deck_type: str
    theme: Literal["light", "dark"]
    slide_count: int
    extra_instructions: Optional[str] = None
    user_data: Dict[str, Any] = Field(default_factory=dict)

def collect_requirements_interactive(initial_topic: Optional[str] = None) -> DeckRequirements:
    """Prompt the user for inputs using rich-based terminal QA."""
    console.print(Panel.fit(
        "[bold teal]Welcome to ppt-gen Requirements Wizard[/bold teal]\n"
        "Let's gather some details to generate your slide deck.",
        border_style="teal"
    ))

    # Topic
    if not initial_topic:
        topic = Prompt.ask("[bold]What is the topic or objective of this deck?[/bold]")
    else:
        topic = initial_topic
        console.print(f"[bold]Topic:[/bold] {topic}")

    # Audience
    audience = Prompt.ask(
        "[bold]Who is the target audience?[/bold]",
        default="Executive Leadership"
    )

    # Deck Type
    deck_type = Prompt.ask(
        "[bold]Select a deck type / preset[/bold]",
        choices=["consulting_strategy", "business_review", "market_analysis", "product_dashboard", "executive_summary", "custom"],
        default="consulting_strategy"
    )

    # Theme
    theme_str = Prompt.ask(
        "[bold]Select a style theme[/bold]",
        choices=["light", "dark"],
        default="light"
    )
    theme: Literal["light", "dark"] = "light" if theme_str == "light" else "dark"

    # Slide Count
    slide_count = IntPrompt.ask(
        "[bold]How many slides should the deck contain (approximate)?[/bold]",
        default=6
    )

    # User supplied real numbers (optional)
    console.print("\n[bold yellow]Optionally plug in real numbers.[/bold yellow]")
    console.print("Use the format [italic]label=value[/italic] separated by commas. E.g.: [italic]conversion_rate=24%, sales_target=10M[/italic]")
    raw_numbers = Prompt.ask(
        "Enter real numbers (press Enter to default to synthetic placeholders)",
        default=""
    )
    
    user_data = {}
    if raw_numbers.strip():
        for item in raw_numbers.split(","):
            if "=" in item:
                k, v = item.split("=", 1)
                user_data[k.strip().lower()] = v.strip()
                
    # Extra instructions
    extra_instructions = Prompt.ask(
        "[bold]Any extra instructions or narrative guidelines? (press Enter to skip)[/bold]",
        default=""
    )
    extra_instructions_opt = extra_instructions if extra_instructions.strip() else None

    return DeckRequirements(
        topic=topic,
        audience=audience,
        deck_type=deck_type,
        theme=theme,
        slide_count=slide_count,
        extra_instructions=extra_instructions_opt,
        user_data=user_data
    )

def get_default_requirements(topic: str, slide_count: int = 6, theme: Literal["light", "dark"] = "light") -> DeckRequirements:
    """Generate default requirements without CLI prompts (used for --fast mode)."""
    return DeckRequirements(
        topic=topic,
        audience="Executive Leadership",
        deck_type="consulting_strategy",
        theme=theme,
        slide_count=slide_count,
        extra_instructions=None,
        user_data={}
    )
