from typing import Tuple, List, Dict
from ppt_gen.core.settings import Settings
from ppt_gen.core.blueprint_library import Blueprint, Slot

# Padding added outward on all four sides of every group background card rectangle.
# This prevents widget border boxes from sitting flush against the card edge,
# eliminating the zero-padding collision bug found in the original audit.
GROUP_CARD_PAD = 0.06  # inches


class LayoutEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pres = settings.presentation

        # Calculate cell dimensions
        avail_w = self.pres.width_inches - self.pres.margin_left - self.pres.margin_right
        total_gutter_w = (self.pres.grid_cols - 1) * self.pres.gutter_width
        self.cell_width = (avail_w - total_gutter_w) / self.pres.grid_cols

        avail_h = self.pres.height_inches - self.pres.margin_top - self.pres.margin_bottom
        total_gutter_h = (self.pres.grid_rows - 1) * self.pres.gutter_height
        self.cell_height = (avail_h - total_gutter_h) / self.pres.grid_rows

    def get_rect_in_inches(self, col: float, row: float, col_span: float, row_span: float) -> Tuple[float, float, float, float]:
        """Translate grid positions to physical inches on the slide: (left, top, width, height)."""
        left = self.pres.margin_left + col * (self.cell_width + self.pres.gutter_width)
        top = self.pres.margin_top + row * (self.cell_height + self.pres.gutter_height)
        width = col_span * self.cell_width + (col_span - 1) * self.pres.gutter_width
        height = row_span * self.cell_height + (row_span - 1) * self.pres.gutter_height
        return left, top, width, height

    def get_group_rect_in_inches(self, slots: List[Slot]) -> Tuple[float, float, float, float]:
        """Compute the bounding box encompassing all slots in a visual group, with padding.

        The returned rectangle is expanded outward by GROUP_CARD_PAD on all four
        sides so the background card has a visible inset around its content widgets.
        Slot coordinates themselves are NOT affected — only the card background grows.
        """
        if not slots:
            return 0.0, 0.0, 0.0, 0.0

        min_col = min(s.grid_area[0] for s in slots)
        min_row = min(s.grid_area[1] for s in slots)
        max_col_end = max(s.grid_area[0] + s.grid_area[2] for s in slots)
        max_row_end = max(s.grid_area[1] + s.grid_area[3] for s in slots)

        col_span = max_col_end - min_col
        row_span = max_row_end - min_row

        inner_left, inner_top, inner_w, inner_h = self.get_rect_in_inches(
            min_col, min_row, col_span, row_span
        )
        # Expand outward by GROUP_CARD_PAD on every side
        pad = GROUP_CARD_PAD
        return (
            inner_left - pad,
            inner_top - pad,
            inner_w + 2 * pad,
            inner_h + 2 * pad,
        )
