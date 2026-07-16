import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from ppt_gen.core.settings import load_settings
from ppt_gen.core.requirements_wizard import collect_requirements_interactive, get_default_requirements
from ppt_gen.core.llm_client import LLMClient
from ppt_gen.core.deck_templates import get_preset_plan, DeckPlan, SlideOutlineItem
from ppt_gen.core.deck_planner import DeckPlanner
from ppt_gen.core.section_planner import SectionPlanner
from ppt_gen.core.outline_checkpoint import run_outline_checkpoint
from ppt_gen.core.slide_generator import SlideGenerator
from ppt_gen.core.content_formatter import format_content
from ppt_gen.core.blueprint_library import get_blueprint
from ppt_gen.core.plan_store import compile_deck_plan, save_deck_plan, load_deck_plan, pregenerate_deck_data
from ppt_gen.core.renderer import PPTXRenderer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cli")

def slugify(text: str) -> str:
    """Generate a filename-friendly slug from text."""
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    slug = re.sub(r"[-\s]+", "_", slug)
    return slug[:40]

def handle_build(args):
    """Orchestrate the full generation pipeline from requirement prompts to final PPTX."""
    topic = args.prompt
    
    # 1. Gather requirements (CLI Wizard vs --fast defaults)
    if args.fast:
        logger.info("Fast mode enabled. Skipping interactive requirements wizard.")
        theme_name = args.theme if args.theme else "light"
        slide_count = args.slides if args.slides else 6
        reqs = get_default_requirements(topic, slide_count=slide_count, theme=theme_name)
    else:
        reqs = collect_requirements_interactive(topic)
        
    # 2. Load settings and theme
    logger.info(f"Loading settings with theme '{reqs.theme}'...")
    settings = load_settings(reqs.theme)
    
    # If cli override flags are set, apply them to settings
    if args.mock:
        logger.info("Enabling offline MOCK mode for LLM generation.")
        mock_mode = True
    else:
        mock_mode = False
        
    llm_client = LLMClient(settings, mock_mode=mock_mode)
    
    # 3. Deck planning & template checking
    logger.info(f"Checking for template preset matching '{reqs.topic}'...")
    preset = get_preset_plan(reqs.deck_type)
    
    if preset and reqs.slide_count == len(preset["slides"]):
        logger.info(f"Found built-in preset '{reqs.deck_type}'. Skipping planning LLM calls.")
        deck_plan = DeckPlan(objective=preset["objective"], sections=preset["sections"])
        slides_outline = [SlideOutlineItem(**s) for s in preset["slides"]]
    else:
        logger.info("Running Deck Planner (LLM #1)...")
        deck_planner = DeckPlanner(llm_client)
        deck_plan = deck_planner.plan_deck(reqs)
        
        logger.info("Running Section Planner (LLM #2)...")
        section_planner = SectionPlanner(llm_client)
        section_planner_output = section_planner.plan_sections(reqs, deck_plan)
        slides_outline = section_planner_output.slides
        
    # 4. Human Outline Checkpoint
    try:
        approved_slides = run_outline_checkpoint(slides_outline, fast_mode=args.fast)
    except KeyboardInterrupt:
        logger.info("Build cancelled at outline review checkpoint.")
        sys.exit(0)
        
    # Set data sources on slides (injecting user numbers if any keys match slot IDs)
    if reqs.user_data:
        logger.info(f"Injecting user-supplied data: {reqs.user_data}")
        # Map values to outline items
        for slide in approved_slides:
            slide.user_data = reqs.user_data
            slide.data_mode = "user_supplied"
            
    # 5. Resolve Synthetic and User-supplied Data First (Data-First Approach)
    logger.info("Pre-generating synthetic numbers and structures for slides...")
    deck_id = slugify(reqs.topic)
    pregenerated_deck = pregenerate_deck_data(deck_id, approved_slides)
    
    # 6. Slide Generation Loop
    generated_slides = []
    slide_generator = SlideGenerator(llm_client)
    
    logger.info(f"Starting generation loop for {len(approved_slides)} slides...")
    for idx, slide_item in enumerate(approved_slides):
        prev_title = approved_slides[idx - 1].slide_title if idx > 0 else None
        next_title = approved_slides[idx + 1].slide_title if idx < len(approved_slides) - 1 else None
        
        # Call LLM #3 to generate contents with pre-generated numbers
        slide_content = slide_generator.generate_slide(
            idx, slide_item, pregenerated_deck[idx], prev_title, next_title
        )
        
        # Apply formatting / layout constraints
        blueprint = get_blueprint(slide_item.archetype)
        formatted_content = format_content(slide_content, blueprint)
        
        generated_slides.append(formatted_content)
        
    # 7. Compile, save, and render
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"{deck_id}_{timestamp}"
    
    plan_path = Path("output") / f"{output_name}.plan.json"
    pptx_path = Path("output") / f"{output_name}.pptx"
    
    logger.info("Merging LLM text copy and pre-generated numbers...")
    full_deck_plan = compile_deck_plan(
        deck_id=deck_id,
        objective=deck_plan.objective,
        theme=reqs.theme,
        slides_outline=approved_slides,
        slides_content=generated_slides,
        pregenerated_deck=pregenerated_deck
    )
    
    # logger.info(f"Saving resolved plan to {plan_path}...")
    # save_deck_plan(full_deck_plan, plan_path)
    
    logger.info(f"Rendering PowerPoint presentation to {pptx_path}...")
    renderer = PPTXRenderer(settings)
    renderer.render_deck(full_deck_plan, pptx_path)
    
    print("\n" + "="*60)
    print(f"BUILD COMPLETED SUCCESSFULLY!")
    print(f"PowerPoint Deck: {pptx_path.resolve()}")
    print("="*60)

def handle_render(args):
    """Fast, LLM-free re-rendering from an existing plan.json file."""
    plan_path = Path(args.plan_file)
    if not plan_path.exists():
        logger.error(f"Plan file not found: {plan_path}")
        sys.exit(1)
        
    logger.info(f"Loading resolved plan from {plan_path}...")
    full_deck_plan = load_deck_plan(plan_path)
    
    # Reload settings using the theme saved in the plan file
    logger.info(f"Loading settings with theme '{full_deck_plan.theme}'...")
    settings = load_settings(full_deck_plan.theme)
    
    # Replace .plan.json with .pptx to overwrite the main presentation
    if plan_path.name.endswith(".plan.json"):
        pptx_name = plan_path.name[:-10] + ".pptx"
        pptx_path = plan_path.parent / pptx_name
    else:
        pptx_path = plan_path.with_suffix(".pptx")
        
    logger.info(f"Re-rendering PowerPoint presentation to {pptx_path}...")
    
    renderer = PPTXRenderer(settings)
    renderer.render_deck(full_deck_plan, pptx_path)
    
    print("\n" + "="*60)
    print(f"RE-RENDER COMPLETED SUCCESSFULLY!")
    print(f"PowerPoint Deck: {pptx_path.resolve()}")
    print("="*60)

def main():
    parser = argparse.ArgumentParser(description="ppt-gen: McKinsey-Style Slide Deck Generator")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to execute")
    
    # build sub-command
    parser_build = subparsers.add_parser("build", help="Generate a new slide deck from a prompt")
    parser_build.add_argument("prompt", type=str, help="Topic or main objective of the slide deck")
    parser_build.add_argument("--fast", action="store_true", help="Skip interactive QA prompts and use templates instantly")
    parser_build.add_argument("--mock", action="store_true", help="Run with mock LLM outputs offline")
    parser_build.add_argument("--theme", default="light", help="Theme palette (light, dark, navy, or custom theme name)")
    parser_build.add_argument("--slides", type=int, default=6, help="Target slide count")
    
    # render sub-command
    parser_render = subparsers.add_parser("render", help="Re-compile a PowerPoint deck from an edited plan.json")
    parser_render.add_argument("plan_file", type=str, help="Path to the plan.json file")
    
    args = parser.parse_args()
    
    if args.command == "build":
        handle_build(args)
    elif args.command == "render":
        handle_render(args)

if __name__ == "__main__":
    main()
