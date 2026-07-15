import sys
from pathlib import Path
import pandas as pd
import gradio as gr

# Ensure the project root is in the path so we can import ppt_gen packages
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ppt_gen.core.settings import load_settings
from ppt_gen.core.llm_client import LLMClient
from ppt_gen.core.deck_templates import get_preset_plan, DeckPlan, SlideOutlineItem
from ppt_gen.core.section_planner import SectionPlanner
from ppt_gen.core.deck_planner import DeckPlanner
from ppt_gen.core.slide_generator import SlideGenerator
from ppt_gen.core.blueprint_library import get_blueprint, ARCHETYPES
from ppt_gen.core.content_formatter import format_content
from ppt_gen.core.plan_store import compile_deck_plan, enrich_captions_with_data, save_deck_plan
from ppt_gen.core.renderer import PPTXRenderer
from ppt_gen.core.validator import validate_deck
from ppt_gen.core.requirements_wizard import DeckRequirements
from cli import slugify
from datetime import datetime

# -----------------------------
# Archetype Mapping for User Friendly UI names
# -----------------------------

ARCHETYPE_MAP = {
    "executive_cover": "Executive Cover",
    "title_challenge": "Title and Challenge",
    "comparison_bars": "Comparison Bars",
    "two_column_initiative": "Two Column Initiative",
    "single_chart_focus": "Single Chart Focus",
    "stat_grid_charts": "Stat Grid and Charts",
    "dashboard_with_table": "Dashboard with Table",
    "table_priorities": "Table and Priorities",
    "closing_takeaways": "Closing Takeaways"
}

def clean_archetype_name(friendly_name: str) -> str:
    """Map friendly user-facing name back to the internal backend string."""
    name_clean = str(friendly_name).strip().lower().replace("_", " ").replace(" & ", " and ")
    for internal, friendly in ARCHETYPE_MAP.items():
        friendly_clean = friendly.lower().replace("_", " ").replace(" & ", " and ")
        if name_clean == friendly_clean or name_clean == internal or name_clean.replace(" ", "") == internal.replace("_", ""):
            return internal
    return "title_challenge"  # fallback

# -----------------------------
# Core Actions
# -----------------------------

def generate_outline_action(
    topic,
    audience,
    deck_type,
    style_theme,
    slides_count,
    metrics,
    instructions,
    mock_mode,
    api_key
):
    """
    Step 1: Parse requirements, load settings, initialize client, and generate outline.
    Returns the dataframe data, outline review visibility, outline state, deck objective state, requirements state, and status.
    """
    try:
        if not topic.strip():
            return None, gr.update(visible=False), None, None, None, "Please enter a presentation topic."

        # Parse metrics (label=value)
        user_data = {}
        if metrics.strip():
            for item in metrics.split(","):
                if "=" in item:
                    k, v = item.split("=", 1)
                    user_data[k.strip().lower()] = v.strip()

        # Build DeckRequirements
        slide_count_int = int(slides_count) if slides_count.strip().isdigit() else 6
        reqs = DeckRequirements(
            topic=topic,
            audience=audience,
            deck_type=deck_type,
            theme=style_theme,
            slide_count=slide_count_int,
            extra_instructions=instructions if instructions.strip() else None,
            user_data=user_data
        )

        # Load settings
        settings = load_settings(reqs.theme)
        if api_key.strip():
            settings.llm.api_key = api_key.strip()

        # Initialize LLM Client
        llm_client = LLMClient(settings, mock_mode=mock_mode)

        # Plan the deck
        preset = get_preset_plan(reqs.deck_type)
        if preset:
            section_planner = SectionPlanner(llm_client)
            custom_preset = section_planner.customize_preset(reqs, preset)
            deck_plan = DeckPlan(objective=custom_preset.objective, sections=custom_preset.sections)
            slides_outline = custom_preset.slides
        else:
            deck_planner = DeckPlanner(llm_client)
            deck_plan = deck_planner.plan_deck(reqs)
            section_planner = SectionPlanner(llm_client)
            section_planner_output = section_planner.plan_sections(reqs, deck_plan)
            slides_outline = section_planner_output.slides

        # Convert to DataFrame
        df_data = []
        for idx, slide in enumerate(slides_outline, 1):
            friendly_arch = ARCHETYPE_MAP.get(slide.archetype, slide.archetype.replace("_", " ").title())
            df_data.append([
                idx,
                slide.section,
                slide.slide_title,
                slide.purpose,
                friendly_arch
            ])

        columns = ["Slide #", "Section", "Title", "Purpose", "Archetype"]
        df = pd.DataFrame(df_data, columns=columns)

        status_msg = "Outline generated successfully! Please review and modify it in the table below."
        return df, gr.update(visible=True), slides_outline, deck_plan.objective, reqs, status_msg

    except Exception as e:
        import traceback
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        return None, gr.update(visible=False), None, None, None, error_msg


def move_slide_up(df, selected_slide_num):
    """Move the specified slide up in the dataframe."""
    if df is None or len(df) == 0:
        return df, "⚠️ No slides to move."
    try:
        slide_num = int(selected_slide_num)
        idx = slide_num - 1
    except ValueError:
        return df, "⚠️ Selected Slide must be a valid integer."

    if idx <= 0 or idx >= len(df):
        return df, f"⚠️ Cannot move slide {slide_num} up."

    # Swap rows using pandas
    df_new = df.copy()
    temp = df_new.iloc[idx].copy()
    df_new.iloc[idx] = df_new.iloc[idx - 1]
    df_new.iloc[idx - 1] = temp

    # Reset slide numbers
    df_new["Slide #"] = range(1, len(df_new) + 1)
    return df_new, f"⬆️ Moved slide {slide_num} up."


def move_slide_down(df, selected_slide_num):
    """Move the specified slide down in the dataframe."""
    if df is None or len(df) == 0:
        return df, "⚠️ No slides to move."
    try:
        slide_num = int(selected_slide_num)
        idx = slide_num - 1
    except ValueError:
        return df, "⚠️ Selected Slide must be a valid integer."

    if idx < 0 or idx >= len(df) - 1:
        return df, f"⚠️ Cannot move slide {slide_num} down."

    # Swap rows using pandas
    df_new = df.copy()
    temp = df_new.iloc[idx].copy()
    df_new.iloc[idx] = df_new.iloc[idx + 1]
    df_new.iloc[idx + 1] = temp

    # Reset slide numbers
    df_new["Slide #"] = range(1, len(df_new) + 1)
    return df_new, f"⬇️ Moved slide {slide_num} down."


def delete_slide_row(df, selected_slide_num):
    """Delete the specified slide from the dataframe."""
    if df is None or len(df) == 0:
        return df, "⚠️ No slides to delete."
    try:
        slide_num = int(selected_slide_num)
        idx = slide_num - 1
    except ValueError:
        return df, "⚠️ Selected Slide must be a valid integer."

    if idx < 0 or idx >= len(df):
        return df, f"⚠️ Invalid slide number {slide_num}."

    # Drop row
    df_new = df.drop(df.index[idx]).reset_index(drop=True)
    df_new["Slide #"] = range(1, len(df_new) + 1)
    return df_new, f"🗑️ Deleted slide {slide_num}."


def add_slide_row(df):
    """Add a new slide row to the end of the dataframe."""
    if df is None:
        df = pd.DataFrame(columns=["Slide #", "Section", "Title", "Purpose", "Archetype"])

    new_num = len(df) + 1
    new_row = {
        "Slide #": new_num,
        "Section": "Next Phase",
        "Title": "New Title Focus",
        "Purpose": "Support core message",
        "Archetype": "Title and Challenge"
    }
    df_new = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df_new, "➕ Added a new slide to the end."


def generate_deck_action(df, deck_objective, reqs, mock_mode, api_key):
    """
    Step 2: Read the approved/edited dataframe outline and run full slide content generation + rendering.
    """
    if df is None or len(df) == 0:
        return "Outline is empty. Generate outline first.", None

    try:
        # Load settings
        settings = load_settings(reqs.theme)
        if api_key.strip():
            settings.llm.api_key = api_key.strip()

        # Initialize LLM Client
        llm_client = LLMClient(settings, mock_mode=mock_mode)

        # Re-build SlideOutlineItem objects from dataframe
        approved_slides = []
        for _, row in df.iterrows():
            backend_arch = clean_archetype_name(str(row["Archetype"]))
            approved_slides.append(SlideOutlineItem(
                section=str(row["Section"]),
                slide_title=str(row["Title"]),
                purpose=str(row["Purpose"]),
                archetype=backend_arch,
                data_mode="synthetic",
                user_data=None
            ))

        # Inject user data numbers
        if reqs.user_data:
            for slide in approved_slides:
                slide.user_data = reqs.user_data
                slide.data_mode = "user_supplied"

        # Slide Generation Loop
        generated_slides = []
        slide_generator = SlideGenerator(llm_client)

        for idx, slide_item in enumerate(approved_slides):
            prev_title = approved_slides[idx - 1].slide_title if idx > 0 else None
            next_title = approved_slides[idx + 1].slide_title if idx < len(approved_slides) - 1 else None

            # Call LLM #3 to generate contents
            slide_content = slide_generator.generate_slide(
                idx, slide_item,
                prev_title=prev_title,
                next_title=next_title,
                deck_objective=deck_objective,
                all_slide_titles=[s.slide_title for s in approved_slides],
                previous_slides_content=generated_slides,
                extra_instructions=reqs.extra_instructions
            )

            # Apply formatting
            blueprint = get_blueprint(slide_item.archetype)
            formatted_content = format_content(slide_content, blueprint)
            generated_slides.append(formatted_content)

        # Compile, save, and render
        deck_id = slugify(reqs.topic)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"{deck_id}_{timestamp}"

        output_dir = project_root / "output"
        output_dir.mkdir(exist_ok=True)

        plan_path = output_dir / f"{output_name}.plan.json"
        pptx_path = output_dir / f"{output_name}.pptx"

        full_deck_plan = compile_deck_plan(
            deck_id=deck_id,
            objective=deck_objective,
            theme=reqs.theme,
            slides_outline=approved_slides,
            slides_content=generated_slides
        )

        # Enrich captions with data (LLM #4)
        full_deck_plan = enrich_captions_with_data(
            plan=full_deck_plan,
            llm_client=llm_client,
            slides_outline=approved_slides
        )

        # Save plan
        save_deck_plan(full_deck_plan, plan_path)

        # Render PowerPoint
        renderer = PPTXRenderer(settings)
        validate_deck(full_deck_plan, ARCHETYPES, renderer.layout_engine)
        renderer.render_deck(full_deck_plan, pptx_path)

        success_msg = f"BUILD COMPLETED SUCCESSFULLY!\n\nPowerPoint file generated at: output/{pptx_path.name}"
        return success_msg, [str(pptx_path), str(plan_path)]

    except Exception as e:
        import traceback
        error_msg = f"Error generating presentation: {str(e)}\n{traceback.format_exc()}"
        return error_msg, None


# -----------------------------
# UI Layout
# -----------------------------

theme = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="gray",
    neutral_hue="slate"
)

with gr.Blocks(
    title="AI PowerPoint Generator Dashboard"
) as demo:

    # States
    slides_outline_state = gr.State()
    deck_objective_state = gr.State()
    reqs_state = gr.State()

    with gr.Column(elem_classes="container"):
        gr.Markdown(
            """
            # AI PowerPoint Generator
            Create consulting-quality presentations using McKinsey-style layouts. Design and edit the slide outline before generating the final presentation deck.
            """
        )

        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Step 1: Presentation Setup")
                
                topic = gr.Textbox(
                    label="Presentation Topic / Core Message",
                    placeholder="Describe your presentation purpose, e.g. Q3 Sales Performance, AI in Retail Operations...",
                    lines=3,
                )

                with gr.Row():
                    audience = gr.Dropdown(
                        choices=[
                            "Executive Leadership",
                            "Management",
                            "Technical Team",
                            "Clients",
                            "Investors",
                            "Students",
                            "General Audience",
                        ],
                        value="Executive Leadership",
                        label="Target Audience",
                    )

                    deck_type = gr.Dropdown(
                        choices=[
                            "consulting_strategy",
                            "business_review",
                            "market_analysis",
                            "product_dashboard",
                            "executive_summary",
                            "insights_report",
                            "transformation_roadmap",
                            "strategic_positioning",
                            "dashboard_deck",
                            "custom",
                        ],
                        value="consulting_strategy",
                        label="Deck Type / Preset Structure",
                    )

                with gr.Row():
                    style_theme = gr.Dropdown(
                        choices=["light", "dark", "navy"],
                        value="light",
                        label="Visual Style Theme",
                    )

                    slides_count = gr.Textbox(
                        value="6",
                        label="Approximate Slide Count",
                    )

                metrics = gr.Textbox(
                    label="Plug In Real Numbers (Optional)",
                    placeholder="e.g. revenue=$12M, conversion_rate=14%, active_users=50k",
                    lines=2,
                )

                instructions = gr.Textbox(
                    label="Additional Guidelines / Tone (Optional)",
                    placeholder="e.g. Focus on risks, keep recommendations action-oriented, include roadmap milestones...",
                    lines=3,
                )

            with gr.Column(scale=1):
                gr.Markdown("### Engine Settings")
                
                mock_mode = gr.Checkbox(
                    label="Mock LLM Mode (Fast & Offline)",
                    value=True,
                )

                api_key = gr.Textbox(
                    label="OpenRouter API Key (Optional)",
                    placeholder="Leave blank to use environment variable or config.toml",
                    type="password",
                )


        generate_outline_btn = gr.Button(
            "Generate Outline Blueprint",
            variant="primary",
        )

        setup_status = gr.Textbox(
            label="Setup Progress Status",
            value="Ready.",
            interactive=False,
        )

        # --------------------------
        # Outline Review Section
        # --------------------------

        with gr.Column(visible=False) as outline_section:
            gr.Markdown("---")
            gr.Markdown("## 📋 Step 2: Outline Review & Blueprint Editing")
            gr.Markdown(
                """
                You can edit the sections, titles, purposes, and archetypes directly in the cells of the table below.
                Use the editing buttons to move slides or modify slide counts.
                """
            )

            # Interactive DataFrame
            slide_table = gr.Dataframe(
                headers=["Slide #", "Section", "Title", "Purpose", "Archetype"],
                datatype=["number", "str", "str", "str", "str"],
                column_count=(5, "fixed"),
                interactive=True,
            )

            with gr.Row():
                with gr.Column(scale=1):
                    selected_slide = gr.Number(
                        label="Selected Slide # (for Move/Delete operations)",
                        value=1,
                        precision=0,
                    )
                with gr.Column(scale=3):
                    with gr.Row():
                        moveup_btn = gr.Button("⬆️ Move Selected Up")
                        movedown_btn = gr.Button("⬇️ Move Selected Down")
                        delete_btn = gr.Button("🗑️ Delete Selected")
                        add_btn = gr.Button("➕ Add Slide to End")

            gr.Markdown("---")
            gr.Markdown("## Step 3: Generate Presentation Deck")

            generate_deck_btn = gr.Button("Generate PowerPoint Presentation", variant="primary")

            deck_status = gr.Textbox(
                label="Generation Process Status",
                interactive=False,
            )

            download_files = gr.File(
                label="Download PowerPoint and Plan Files",
                file_count="multiple",
                interactive=False,
            )

    # --------------------------
    # Click Handlers
    # --------------------------

    generate_outline_btn.click(
        fn=generate_outline_action,
        inputs=[
            topic,
            audience,
            deck_type,
            style_theme,
            slides_count,
            metrics,
            instructions,
            mock_mode,
            api_key,
        ],
        outputs=[
            slide_table,
            outline_section,
            slides_outline_state,
            deck_objective_state,
            reqs_state,
            setup_status,
        ],
    )

    moveup_btn.click(
        fn=move_slide_up,
        inputs=[slide_table, selected_slide],
        outputs=[slide_table, deck_status],
    )

    movedown_btn.click(
        fn=move_slide_down,
        inputs=[slide_table, selected_slide],
        outputs=[slide_table, deck_status],
    )

    delete_btn.click(
        fn=delete_slide_row,
        inputs=[slide_table, selected_slide],
        outputs=[slide_table, deck_status],
    )

    add_btn.click(
        fn=add_slide_row,
        inputs=[slide_table],
        outputs=[slide_table, deck_status],
    )

    generate_deck_btn.click(
        fn=generate_deck_action,
        inputs=[
            slide_table,
            deck_objective_state,
            reqs_state,
            mock_mode,
            api_key,
        ],
        outputs=[
            deck_status,
            download_files,
        ],
    )

import os
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        theme=theme,
        css=".container { max-width: 1100px; margin: auto; padding: 20px; }"
    )