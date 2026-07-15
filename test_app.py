import sys
import os
import pandas as pd
from pathlib import Path

# Add project root to sys.path so python can resolve imports
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from app import (
    generate_outline_action,
    move_slide_up,
    move_slide_down,
    delete_slide_row,
    add_slide_row,
    generate_deck_action
)

def test_pipeline():
    print("🚀 Starting automated integration test...")
    
    # 1. Test generate_outline_action
    print("Testing generate_outline_action...")
    topic = "Strategic Plan for AI integration in Retail Operations"
    audience = "Executive Leadership"
    deck_type = "consulting_strategy"
    style_theme = "light"
    slides_count = "4"
    metrics = "revenue=$15M, conversion_rate=12%, growth=20%"
    instructions = "Focus on operational efficiency"
    mock_mode = True
    api_key = ""
    
    df, outline_sec_update, slides_outline, objective, reqs, status = generate_outline_action(
        topic, audience, deck_type, style_theme, slides_count, metrics, instructions, mock_mode, api_key
    )
    
    assert df is not None, "DataFrame should not be None"
    num_slides = len(df)
    assert num_slides > 0, "DataFrame should not be empty"
    assert slides_outline is not None, "slides_outline should not be None"
    assert objective is not None, "objective should not be None"
    assert reqs is not None, "reqs should not be None"
    assert "successfully" in status, f"Expected success status, got: {status}"
    print("✅ generate_outline_action passed.")
    
    # 2. Test move_slide_up / move_slide_down
    print("Testing slide reordering...")
    original_titles = list(df["Title"])
    
    # Move slide 2 up (swapping with slide 1)
    df, msg = move_slide_up(df, 2)
    assert df.iloc[0]["Title"] == original_titles[1], "Slide 2 should now be at position 0"
    assert df.iloc[1]["Title"] == original_titles[0], "Slide 1 should now be at position 1"
    print("✅ move_slide_up passed.")
    
    # Move slide 1 down (swapping back)
    df, msg = move_slide_down(df, 1)
    assert df.iloc[0]["Title"] == original_titles[0], "Slide 1 should be back at position 0"
    assert df.iloc[1]["Title"] == original_titles[1], "Slide 2 should be back at position 1"
    print("✅ move_slide_down passed.")
    
    # 3. Test delete_slide_row / add_slide_row
    print("Testing slide insertion/deletion...")
    df, msg = delete_slide_row(df, 3)
    assert len(df) == num_slides - 1, f"DataFrame should have {num_slides - 1} rows after deletion, got {len(df)}"
    
    df, msg = add_slide_row(df)
    assert len(df) == num_slides, f"DataFrame should have {num_slides} rows after addition, got {len(df)}"
    assert df.iloc[-1]["Archetype"] == "Title and Challenge", "New slide archetype should be Title and Challenge"
    print("✅ slide insertion/deletion passed.")
    
    # 4. Test generate_deck_action
    print("Testing generate_deck_action (Mock Mode)...")
    success_msg, files = generate_deck_action(
        df, objective, reqs, mock_mode=True, api_key=""
    )
    
    assert files is not None, "files should not be None"
    assert len(files) == 2, f"Should return 2 files (.pptx and .plan.json), got {len(files)}"
    
    pptx_path = Path(files[0])
    plan_path = Path(files[1])
    
    assert pptx_path.exists(), f"PowerPoint file does not exist: {pptx_path}"
    assert plan_path.exists(), f"Plan JSON file does not exist: {plan_path}"
    
    print(f"✅ generate_deck_action passed. Output pptx: {pptx_path.name}")
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_pipeline()
