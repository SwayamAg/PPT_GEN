import os
from pathlib import Path
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from ppt_gen.core.deck_templates import SlideOutlineItem

console = Console()

def generate_markdown_outline(slides: List[SlideOutlineItem]) -> str:
    """Generate a clean, editable markdown representation of the slides."""
    lines = [
        "# Slide Deck Outline Review",
        "Instructions: You can edit the Slide Titles, Purposes, Sections, or Archetypes directly in this file.",
        "Save this file when done, then return to the terminal and confirm to proceed.",
        "Do NOT change the line prefixes (e.g. 'Title:', 'Archetype:').",
        "Available Archetypes: executive_cover, title_challenge, comparison_bars, two_column_initiative, single_chart_focus, stat_grid_charts, dashboard_with_table, table_priorities, closing_takeaways",
        ""
    ]
    
    for idx, slide in enumerate(slides, 1):
        lines.extend([
            f"## Slide {idx}",
            f"Title: {slide.slide_title}",
            f"Purpose: {slide.purpose}",
            f"Archetype: {slide.archetype}",
            f"Section: {slide.section}",
            ""
        ])
        
    return "\n".join(lines)

def parse_markdown_outline(content: str) -> List[SlideOutlineItem]:
    """Parse the edited markdown outline back into SlideOutlineItem objects."""
    slides = []
    current_slide = {}
    
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("## Slide"):
            if current_slide:
                # Ensure fields are present with safe fallbacks
                slides.append(SlideOutlineItem(
                    section=current_slide.get("section", "Executive Summary"),
                    slide_title=current_slide.get("slide_title", "Untitled Slide"),
                    purpose=current_slide.get("purpose", "General overview"),
                    archetype=current_slide.get("archetype", "title_challenge"),
                    data_mode="synthetic",
                    user_data=None
                ))
                current_slide = {}
        elif line.startswith("Title:"):
            current_slide["slide_title"] = line.split(":", 1)[1].strip()
        elif line.startswith("Purpose:"):
            current_slide["purpose"] = line.split(":", 1)[1].strip()
        elif line.startswith("Archetype:"):
            current_slide["archetype"] = line.split(":", 1)[1].strip()
        elif line.startswith("Section:"):
            current_slide["section"] = line.split(":", 1)[1].strip()
            
    if current_slide:
        slides.append(SlideOutlineItem(
            section=current_slide.get("section", "Executive Summary"),
            slide_title=current_slide.get("slide_title", "Untitled Slide"),
            purpose=current_slide.get("purpose", "General overview"),
            archetype=current_slide.get("archetype", "title_challenge"),
            data_mode="synthetic",
            user_data=None
        ))
        
    return slides

def run_outline_checkpoint(slides: List[SlideOutlineItem], fast_mode: bool = False) -> List[SlideOutlineItem]:
    """Present the outline to the user, wait for manual edits (unless fast_mode is on)."""
    if fast_mode:
        console.print("[yellow]Fast mode enabled. Auto-approving generated outline.[/yellow]")
        return slides

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    outline_file = output_dir / "outline_review.md"
    
    # Write initial editable outline
    markdown_content = generate_markdown_outline(slides)
    with open(outline_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    console.print(Panel.fit(
        f"[bold green]Outline Checkpoint Created![/bold green]\n"
        f"A review file has been generated at: [cyan]{outline_file.resolve()}[/cyan]\n\n"
        "1. Open this file in your favorite text editor.\n"
        "2. Review/edit slide titles, archetypes, and purposes.\n"
        "3. Save the file.\n"
        "4. Return here and confirm to continue.",
        title="Outline Review Required",
        border_style="green"
    ))
    
    # Wait for user confirmation
    confirmed = Confirm.ask("Have you saved your changes and wish to proceed?", default=True)
    
    if not confirmed:
        console.print("[yellow]Aborting execution. You can resume with the plan file.[/yellow]")
        raise KeyboardInterrupt("User cancelled the run.")
        
    # Read the modified outline back
    with open(outline_file, "r", encoding="utf-8") as f:
        edited_content = f.read()
        
    edited_slides = parse_markdown_outline(edited_content)
    console.print(f"[bold green]Successfully loaded {len(edited_slides)} slides from outline review.[/bold green]")
    return edited_slides
