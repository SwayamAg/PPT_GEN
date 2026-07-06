import os
import sys
import unittest
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ppt_gen.core.settings import load_settings
from ppt_gen.core.synthetic_data import infer_direction, get_deterministic_seed, SyntheticDataEngine
from ppt_gen.core.typography import wrap_text, get_text_height, find_optimal_font_size
from ppt_gen.core.layout_engine import LayoutEngine
from ppt_gen.core.blueprint_library import get_blueprint

class TestPPTGen(unittest.TestCase):
    def test_settings_load(self):
        """Test that settings load successfully and resolve theme structures."""
        settings = load_settings("light")
        self.assertEqual(settings.presentation.grid_cols, 12)
        self.assertEqual(settings.presentation.grid_rows, 8)
        self.assertIsNotNone(settings.theme)
        self.assertEqual(settings.theme.background, "#FBFBF9")

    def test_synthetic_data_direction(self):
        """Test keyword direction lookup matches corporate context."""
        self.assertEqual(infer_direction("Reduction in acquisition cost"), "down")
        self.assertEqual(infer_direction("Projected Market Share Recovery"), "up")
        self.assertEqual(infer_direction("Standard operations"), "up")  # Default fallback

    def test_deterministic_seed(self):
        """Verify that seeds are stable and reproducible across program runs."""
        s1 = get_deterministic_seed("deck1", 2, "kpi_left")
        s2 = get_deterministic_seed("deck1", 2, "kpi_left")
        s3 = get_deterministic_seed("deck1", 2, "kpi_right")
        self.assertEqual(s1, s2)
        self.assertNotEqual(s1, s3)

    def test_synthetic_primitives(self):
        """Validate shape output formats and ranges from the Synthetic Data Engine."""
        engine = SyntheticDataEngine(deck_id="test_deck")
        
        # Stat multiplier
        val_mult = engine.generate_slot_value(0, "slot1", "Increase scale fold", "single_stat")
        self.assertTrue(val_mult.endswith("x"))
        
        # Stat rate
        val_rate = engine.generate_slot_value(0, "slot2", "Reduction in churn rate", "single_stat")
        self.assertTrue("↓" in val_rate)
        
        # Trend series
        trend = engine.generate_slot_value(1, "chart1", "Revenue growth", "trend_series")
        self.assertIn("labels", trend)
        self.assertIn("series", trend)
        self.assertEqual(len(trend["labels"]), 6)
        self.assertEqual(len(trend["series"]), 2)

    def test_layout_coordinates(self):
        """Test cell bounding box logic with margins and gutters."""
        settings = load_settings("light")
        engine = LayoutEngine(settings)
        
        # (col, row, col_span, row_span)
        # Margin is 0.5 inches on each side. Total width 13.33. Grid cols = 12. Gutter = 0.15.
        # Check that top-left cell starts at margin limits
        left, top, width, height = engine.get_rect_in_inches(0, 0, 1, 1)
        self.assertAlmostEqual(left, 0.5)
        self.assertAlmostEqual(top, 0.5)
        self.assertAlmostEqual(width, engine.cell_width)
        self.assertAlmostEqual(height, engine.cell_height)

if __name__ == "__main__":
    unittest.main()
