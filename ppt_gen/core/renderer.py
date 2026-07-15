import logging
import io
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_AUTO_SIZE, MSO_ANCHOR

from ppt_gen.core.settings import Settings
from ppt_gen.core.blueprint_library import get_blueprint
from ppt_gen.core.plan_store import FullDeckPlan
from ppt_gen.core.layout_engine import LayoutEngine
from ppt_gen.core.overflow import audit_text_fit
from ppt_gen.core.chart_engine import render_chart
from ppt_gen.core.chart_engine_native import render_native_chart
from ppt_gen.core import business_widgets as bw
from ppt_gen.core.icon_library import resolve_icon

logger = logging.getLogger("renderer")


def estimate_insight_height(text: str, width_inches: float) -> float:
    """Calculate the required height for an insight text box dynamically using compact 10pt sizing."""
    if not text:
        return 0.0
    # Average char width at 10pt is about 0.05 inches.
    # Text box width has 0.16 margins total (0.08 on each side) plus some safe clearance.
    text_width_in = width_inches - 0.16
    chars_per_line = max(12, int(text_width_in / 0.05))
    lines_count = max(1, (len(text) + chars_per_line - 1) // chars_per_line)
    # Line height is roughly 0.16 inches at 10pt font size, plus padding
    return lines_count * 0.16 + 0.08


def hex_to_rgb(hex_str: str) -> RGBColor:
    """Helper to convert a #RRGGBB string to a python-pptx RGBColor object."""
    hex_str = hex_str.lstrip('#')
    return RGBColor(*(int(hex_str[i:i+2], 16) for i in (0, 2, 4)))

class PPTXRenderer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.theme = settings.theme
        self.layout_engine = LayoutEngine(settings)

    def render_deck(self, plan: FullDeckPlan, output_pptx_path: Path):
        """Assemble the complete presentation slide deck using python-pptx."""
        prs = Presentation()
        prs.slide_width = Inches(self.settings.presentation.width_inches)
        prs.slide_height = Inches(self.settings.presentation.height_inches)

        # Use a blank slide layout (index 6 in default templates is usually empty)
        blank_layout = prs.slide_layouts[6]

        for idx, r_slide in enumerate(plan.slides):
            logger.info(f"Rendering slide {idx + 1}: {r_slide.title}")
            slide = prs.slides.add_slide(blank_layout)

            # Retrieve blueprint rules (needed to resolve background variant)
            blueprint = get_blueprint(r_slide.archetype)
            slots_map = {s.id: s for s in blueprint.slots}

            # Phase D: title/closing archetypes render on the theme's
            # title_slide_background when declared (e.g. navy cover slide).
            # Falls back to the standard background for themes without it.
            is_title_slide = getattr(blueprint, "background", "content") == "title"
            if is_title_slide and getattr(self.theme, "title_slide_background", None):
                slide_bg = self.theme.title_slide_background
            else:
                slide_bg = self.theme.background

            # Set background color
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = hex_to_rgb(slide_bg)

            # Phase H: compute whether this slide has a dark background so
            # widget renderers can flip text/icon colors for readability.
            self._dark_mode = self._is_dark_bg(slide_bg)

            # Step 1: Render group container card background boxes
            # On dark slides, card backgrounds are translucent / dark-tinted.
            unique_groups = set(s.group for s in blueprint.slots if s.group)
            for group_id in unique_groups:
                group_slots = [s for s in blueprint.slots if s.group == group_id]
                left, top, width, height = self.layout_engine.get_group_rect_in_inches(group_slots)

                card_shape = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
                )

                if self._dark_mode:
                    # On dark backgrounds use a semi-transparent dark card
                    card_shape.fill.solid()
                    card_shape.fill.fore_color.rgb = self._darken(slide_bg, 0.85)
                    card_shape.line.color.rgb = self._darken(slide_bg, 0.65)
                    card_shape.line.width = Pt(0.5)
                elif group_id == "challenge_box":
                    card_shape.fill.solid()
                    card_shape.fill.fore_color.rgb = hex_to_rgb(self.theme.accent_quaternary)
                    card_shape.line.color.rgb = hex_to_rgb(self.theme.accent_quaternary)
                else:
                    card_shape.fill.solid()
                    card_shape.fill.fore_color.rgb = hex_to_rgb(self.theme.card_bg)
                    card_shape.line.color.rgb = hex_to_rgb(self.theme.card_border)
                    card_shape.line.width = Pt(0.75)

            # Step 2: Render individual slot widgets
            for slot_id, payload in r_slide.slots.items():
                slot = slots_map.get(slot_id)
                if not slot:
                    continue

                left, top, width, height = self.layout_engine.get_rect_in_inches(*slot.grid_area)

                if slot.widget == "text":
                    self._render_text_widget(slide, slot, payload, left, top, width, height)
                elif slot.widget in ("stat_callout", "kpi_pill"):
                    self._render_stat_widget(slide, slot, payload, left, top, width, height)
                elif slot.widget in ("numbered_step", "priority_card"):
                    self._render_step_widget(slide, slot, payload, left, top, width, height)
                elif slot.widget == "chart_panel":
                    self._render_chart_widget(slide, idx, slot, payload, left, top, width, height)
                elif slot.widget == "table_panel":
                    self._render_table_widget(slide, slot, payload, left, top, width, height)
                # ── Tier A widgets (business_widgets.py) ──────────────────
                elif slot.widget == "kpi_card":
                    bw.render_kpi_card(
                        slide, payload, self.theme, left, top, width, height,
                        header_font=self.settings.typography.header_font,
                        body_font=self.settings.typography.body_font,
                        dark_mode=self._dark_mode
                    )
                elif slot.widget == "progress_indicator":
                    bw.render_progress_indicator(
                        slide, payload, self.theme, left, top, width, height,
                        header_font=self.settings.typography.header_font,
                        body_font=self.settings.typography.body_font
                    )
                elif slot.widget == "growth_arrow":
                    bw.render_growth_arrow(
                        slide, payload, self.theme, left, top, width, height,
                        header_font=self.settings.typography.header_font,
                        body_font=self.settings.typography.body_font
                    )
                elif slot.widget == "benchmark_bar":
                    bw.render_benchmark_bar(
                        slide, payload, self.theme, left, top, width, height,
                        header_font=self.settings.typography.header_font,
                        body_font=self.settings.typography.body_font
                    )
                elif slot.widget == "market_share_strip":
                    bw.render_market_share_strip(
                        slide, payload, self.theme, left, top, width, height,
                        header_font=self.settings.typography.header_font,
                        body_font=self.settings.typography.body_font
                    )
                elif slot.widget == "scorecard":
                    bw.render_scorecard(
                        slide, payload, self.theme, left, top, width, height,
                        header_font=self.settings.typography.header_font,
                        body_font=self.settings.typography.body_font
                    )
                elif slot.widget == "matrix_view":
                    bw.render_matrix_view(
                        slide, payload, self.theme, left, top, width, height,
                        header_font=self.settings.typography.header_font,
                        body_font=self.settings.typography.body_font
                    )
                elif slot.widget == "variance_graphic":
                    bw.render_variance_graphic(
                        slide, payload, self.theme, left, top, width, height,
                        header_font=self.settings.typography.header_font,
                        body_font=self.settings.typography.body_font
                    )
                elif slot.widget == "eyebrow":
                    self._render_eyebrow_widget(slide, payload, left, top, width, height)
                elif slot.widget == "footer":
                    self._render_footer_widget(slide, payload, left, top, width, height)
                # ── Phase 2 extension: new visual widgets ─────────────────
                elif slot.widget == "chevron_flow":
                    bw.render_chevron_flow(
                        slide, payload, self.theme, left, top, width, height,
                        header_font=self.settings.typography.header_font,
                        body_font=self.settings.typography.body_font,
                        dark_mode=self._dark_mode
                    )
                elif slot.widget == "gantt_strip":
                    bw.render_gantt_strip(
                        slide, payload, self.theme, left, top, width, height,
                        header_font=self.settings.typography.header_font,
                        body_font=self.settings.typography.body_font,
                        dark_mode=self._dark_mode
                    )
                elif slot.widget == "venn_diagram":
                    bw.render_venn_diagram(
                        slide, payload, self.theme, left, top, width, height,
                        header_font=self.settings.typography.header_font,
                        body_font=self.settings.typography.body_font,
                        dark_mode=self._dark_mode
                    )
                elif slot.widget == "pie_chart":
                    bw.render_pie_chart(
                        slide, payload, self.theme, left, top, width, height,
                        header_font=self.settings.typography.header_font,
                        body_font=self.settings.typography.body_font,
                        dark_mode=self._dark_mode
                    )

        # Save output presentation
        output_pptx_path.parent.mkdir(exist_ok=True, parents=True)
        prs.save(str(output_pptx_path))
        import os
        print("RENDERER SAVE EXISTS:", os.path.exists(str(output_pptx_path)))
        print("RENDERER SAVE PATH:", str(output_pptx_path))
        logger.info(f"Presentation saved successfully to {output_pptx_path}")

    # ── Phase H dark-mode helpers ───────────────────────────────────────────
    @staticmethod
    def _is_dark_bg(hex_color: str) -> bool:
        """Return True if *hex_color* has a luminance below the midpoint."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (0.299 * r + 0.587 * g + 0.114 * b) < 140

    def _darken(self, hex_color: str, factor: float = 0.85) -> RGBColor:
        """Darken (or lighten if factor > 1) a hex color toward black."""
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
        r, g, b = int(r * factor), int(g * factor), int(b * factor)
        return RGBColor(min(r, 255), min(g, 255), min(b, 255))

    def _light(self, fallback_hex: str) -> str:
        """Return a light text color for dark backgrounds.

        Uses the theme's accent_secondary (gold in navy) as headline text on
        dark slides, or white (#FFFFFF) as a universal safe default.
        """
        if self._dark_mode:
            return "#FFFFFF"
        return fallback_hex

    def _dark_light(self, dark_hex: str, light_hex: str) -> str:
        """Return dark_hex if content slide, light_hex if title/dark slide."""
        return light_hex if self._dark_mode else dark_hex

    # ── Phase E helpers ──────────────────────────────────────────────────────
    def _add_icon_picture(self, slide, icon_name: Optional[str],
                          left: float, top: float,
                          size: float = 0.28,
                          color_hex: Optional[str] = None):
        """Resolve *icon_name* via icon_library, recolor, and embed as picture.

        Returns True if an icon was drawn, False otherwise (degrades silently).
        """
        if not icon_name:
            return False
        c = color_hex or self.theme.accent_primary
        icon_bytes = resolve_icon(icon_name, c)
        if icon_bytes is None:
            return False
        img = Image.open(io.BytesIO(icon_bytes))
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name)
            slide.shapes.add_picture(
                tmp.name, Inches(left), Inches(top), Inches(size), Inches(size)
            )
        return True

    def _render_text_widget(self, slide, slot, payload, left, top, width, height):
        text = payload.get("text", "")
        if not text:
            return

        # Is it slide header?
        is_header = (slot.id == "title")
        is_subtitle = (slot.id == "subtitle")

        # Deduct margins and bullet indents to align with actual printable area
        has_bullets = "•" in text
        margin_w = 0.34 if has_bullets else 0.04
        margin_h = 0.04

        opt_size, fitting_lines = audit_text_fit(text, width - margin_w, height - margin_h, self.settings, is_header)

        tx_box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.02)

        # Split text into original paragraphs
        paragraphs = text.split("\n")
        # Filter out empty paragraphs if they are consecutive, keeping max one empty line
        clean_paragraphs = []
        for p_text in paragraphs:
            p_clean = p_text.strip()
            if p_clean or (clean_paragraphs and clean_paragraphs[-1]):
                clean_paragraphs.append(p_clean)

        # Phase H: pick colors based on dark/light background
        if is_header:
            head_color = self._dark_light(self.theme.accent_primary, "#FFFFFF")
        elif is_subtitle:
            head_color = self._dark_light(self.theme.text_primary, "#FFFFFFCC")
        else:
            head_color = self._dark_light(self.theme.text_primary, "#FFFFFFCC")
        body_color = self._dark_light(self.theme.text_primary, "#FFFFFFCC")

        # Fallback truncation flow: if we hit the floor size (9) and still overflow, render fitting_lines directly
        is_truncated_flow = False
        if opt_size == 9:
            try:
                from PIL import ImageFont
                from ppt_gen.core.typography import wrap_text
                font_size_px = int(9 * (96.0 / 72.0))
                font = ImageFont.truetype(self.settings.typography.font_path, font_size_px)
                total_lines_at_9 = len(wrap_text(text, font, Inches(width - margin_w) * 96.0))
                if len(fitting_lines) < total_lines_at_9:
                    is_truncated_flow = True
            except Exception:
                pass

        if is_truncated_flow:
            for p_idx, line_text in enumerate(fitting_lines):
                p = tf.paragraphs[0] if p_idx == 0 else tf.add_paragraph()
                p.text = line_text
                p.font.name = self.settings.typography.header_font if is_header else self.settings.typography.body_font
                p.font.size = Pt(opt_size)
                p.font.bold = is_header
                p.font.color.rgb = hex_to_rgb(head_color if p_idx == 0 else body_color)
                p.space_after = Pt(0)
                p.line_spacing = 1.0
        else:
            # Render paragraph-by-paragraph
            for p_idx, para_text in enumerate(clean_paragraphs):
                p = tf.paragraphs[0] if p_idx == 0 else tf.add_paragraph()
                
                # Check if this paragraph is a bullet point
                is_bullet = False
                if para_text.startswith("•"):
                    is_bullet = True
                    para_text = para_text[1:].strip()

                p.text = para_text
                p.font.name = self.settings.typography.header_font if is_header else self.settings.typography.body_font
                p.font.size = Pt(opt_size)
                p.font.bold = is_header
                p.font.color.rgb = hex_to_rgb(head_color if p_idx == 0 else body_color)

                # Set space_after and line_spacing dynamically
                p.space_after = Pt(opt_size * 0.4) if opt_size < 14 else Pt(opt_size * 0.6)
                if opt_size < 12:
                    p.line_spacing = 1.05
                else:
                    p.line_spacing = 1.25

                if is_bullet:
                    p.text = f"•\t{para_text}"
                    try:
                        pPr = p._p.get_or_add_pPr()
                        pPr.set('marL', '274320')   # 0.30 inches in EMUs
                        pPr.set('indent', '-274320') # hanging indent
                    except Exception:
                        pass

    def _render_stat_widget(self, slide, slot, payload, left, top, width, height):
        value = payload.get("value", "")
        label = payload.get("label", "")
        icon_name = payload.get("icon")  # Phase E: optional icon

        icon_size = 0.28
        icon_drawn = False

        # Phase H dark-mode: icon and value colors
        icon_color = self._dark_light(self.theme.accent_primary, "#FFFFFF")
        val_color = self._dark_light(self.theme.accent_primary, "#FFFFFF")
        lbl_color = self._dark_light(self.theme.text_secondary, "#FFFFFFAA")

        if slot.widget == "stat_callout":
            # Phase E: if icon present, lay out [icon | value+label] side-by-side
            if icon_name:
                icon_drawn = self._add_icon_picture(
                    slide, icon_name, left + 0.02, top + 0.08, icon_size,
                    color_hex=icon_color
                )
            text_left = left + (icon_size + 0.08) if icon_drawn else left + 0.04
            text_w = width - (icon_size + 0.12) if icon_drawn else width - 0.08

            tx_box = slide.shapes.add_textbox(Inches(text_left), Inches(top), Inches(text_w), Inches(height))
            tf = tx_box.text_frame
            tf.word_wrap = True
            tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.04)

            # Stat callout: Value on top (big), Label below
            val_size = max(16, min(28, int(height * 18.0)))
            lbl_size = max(9, min(14, int(height * 8.5)))

            p1 = tf.paragraphs[0]
            p1.text = value
            p1.font.name = self.settings.typography.header_font
            p1.font.size = Pt(val_size)
            p1.font.bold = True
            p1.font.color.rgb = hex_to_rgb(val_color)

            p2 = tf.add_paragraph()
            p2.text = label
            p2.font.name = self.settings.typography.body_font
            p2.font.size = Pt(lbl_size)
            p2.font.color.rgb = hex_to_rgb(lbl_color)
        else:
            # KPI pill: icon inline left, then value+label
            if icon_name:
                icon_drawn = self._add_icon_picture(
                    slide, icon_name, left + 0.02, top + 0.06, size=0.22,
                    color_hex=icon_color
                )
            pill_left = left + (0.28) if icon_drawn else left + 0.04
            pill_w = width - (0.32) if icon_drawn else width - 0.08

            tx_box = slide.shapes.add_textbox(Inches(pill_left), Inches(top), Inches(pill_w), Inches(height))
            tf = tx_box.text_frame
            tf.word_wrap = True
            tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.04)

            # Proportional font scaling for kpi pill
            pill_size = max(10, min(16, int(height * 11.0)))

            p1 = tf.paragraphs[0]
            p1.text = f"{value}  —  {label}" if value else label
            p1.font.name = self.settings.typography.body_font
            p1.font.size = Pt(pill_size)
            p1.font.bold = True
            p1.font.color.rgb = hex_to_rgb(self._dark_light(self.theme.text_primary, "#FFFFFF"))

    def _render_step_widget(self, slide, slot, payload, left, top, width, height):
        badge = payload.get("badge", "")
        title = payload.get("title", "")
        desc = payload.get("desc", "")
        icon_name = payload.get("icon")  # Phase E: optional icon

        icon_size = 0.24
        icon_drawn = False
        icon_color = self._dark_light(self.theme.accent_primary, "#FFFFFF")
        if icon_name:
            icon_drawn = self._add_icon_picture(
                slide, icon_name, left + 0.02, top + 0.08, icon_size,
                color_hex=icon_color
            )

        # Only render badge if it is a non-empty, meaningful label (not auto "01".."09")
        _badge_is_meaningful = badge and not (len(badge) <= 2 and badge.lstrip('0').isdigit())
        text_left = left + (icon_size + 0.08) if icon_drawn else left + 0.04
        text_w = width - (icon_size + 0.12) if icon_drawn else width - 0.08

        tx_box = slide.shapes.add_textbox(Inches(text_left), Inches(top), Inches(text_w), Inches(height))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.04)

        # Phase H dark-aware colors
        title_color = self._dark_light(self.theme.accent_primary, "#FFFFFF")
        desc_color = self._dark_light(self.theme.text_secondary, "#FFFFFFAA")

        # Proportional font scaling to prevent text leakage
        base_size = max(9, min(13, int(height * 8.5)))
        title_size = base_size + 2
        desc_size = base_size

        # Paragraph 1: Badge + Title (badge only if meaningful)
        p1 = tf.paragraphs[0]
        p1.text = f"{badge}  {title}" if _badge_is_meaningful else title
        p1.font.name = self.settings.typography.header_font
        p1.font.size = Pt(title_size)
        p1.font.bold = True
        p1.font.color.rgb = hex_to_rgb(title_color)

        # Paragraph 2: Description
        if desc:
            p2 = tf.add_paragraph()
            p2.text = desc
            p2.font.name = self.settings.typography.body_font
            p2.font.size = Pt(desc_size)
            p2.font.color.rgb = hex_to_rgb(desc_color)

    def _render_chart_widget(self, slide, slide_idx, slot, payload, left, top, width, height):
        title = payload.get("title", "")
        insight = payload.get("insight_caption", "")
        chart_data = payload.get("chart_data", {})
        chart_type = payload.get("chart_type", "line")

        title_h = 0.3  # Tighter header — gives chart more vertical room
        
        # Calculate dynamic insight height if there is an insight caption and widget is tall enough
        render_insight = insight and (height >= 2.4)
        insight_h = 0.0
        if render_insight:
            insight_h = estimate_insight_height(insight, width)
            # Clamp insight_h to prevent it from devouring the chart area
            if insight_h > 0.7:
                insight_h = 0.7

        # Title text box (Phase H: dark-aware)
        title_color = self._dark_light(self.theme.text_primary, "#FFFFFF")
        if title:
            tx_box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(title_h))
            p = tx_box.text_frame.paragraphs[0]
            p.text = title
            p.font.name = self.settings.typography.header_font
            p.font.size = Pt(12)  # Reduced from 16pt — gives charts more room
            p.font.bold = True
            p.font.color.rgb = hex_to_rgb(title_color)

        # Chart drawing region (below the title, above the insight box)
        chart_w = width - 0.2
        chart_h = height - title_h - insight_h - 0.1
        chart_left = left + 0.1
        chart_top = top + title_h

        # Phase F: prefer native editable PPTX charts when the type is supported
        # and settings.charts.native is enabled; otherwise render Matplotlib PNG.
        drew_native = False
        if getattr(self.settings.charts, "native", False) and chart_data:
            drew_native = render_native_chart(
                chart_type, chart_data, slide, self.theme,
                chart_left, chart_top, chart_w, chart_h
            )

        if not drew_native:
            charts_dir = Path("output/charts")
            chart_path = charts_dir / f"slide_{slide_idx}_{slot.id}.png"
            render_chart(
                chart_type=chart_type,
                chart_data=chart_data,
                output_path=chart_path,
                theme=self.theme,
                width_in=chart_w,
                height_in=chart_h
            )
            if chart_path.exists():
                slide.shapes.add_picture(
                    str(chart_path),
                    Inches(chart_left), Inches(chart_top),
                    Inches(chart_w), Inches(chart_h)
                )

        # Insight caption as filled box (Phase C)
        if render_insight:
            self._add_insight_box(
                slide, insight,
                left, top + title_h + chart_h + 0.05, width, insight_h
            )

    def _render_table_widget(self, slide, slot, payload, left, top, width, height):
        title = payload.get("title", "")
        insight = payload.get("insight_caption", "")
        headers = payload.get("headers", [])
        rows = payload.get("rows", [])

        title_h = 0.3  # Tighter title — gives table more rows
        
        # Calculate dynamic insight height if there is an insight caption and widget is tall enough
        render_insight = insight and (height >= 2.5)
        insight_h = 0.0
        if render_insight:
            insight_h = estimate_insight_height(insight, width)
            if insight_h > 0.7:
                insight_h = 0.7

        # Phase H dark-aware title
        title_color = self._dark_light(self.theme.text_primary, "#FFFFFF")
        if title:
            tx_box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(title_h))
            p = tx_box.text_frame.paragraphs[0]
            p.text = title
            p.font.name = self.settings.typography.header_font
            p.font.size = Pt(16)
            p.font.bold = True
            p.font.color.rgb = hex_to_rgb(title_color)

        if not headers or not rows:
            return

        cols_count = len(headers)
        rows_count = len(rows) + 1  # headers + data rows

        table_top = top + title_h
        table_h = height - title_h - insight_h - 0.1

        # Add table
        table_shape = slide.shapes.add_table(
            rows_count, cols_count, Inches(left), Inches(table_top), Inches(width), Inches(table_h)
        )
        table = table_shape.table

        # Set column widths
        col_width = width / cols_count
        for col in table.columns:
            col.width = Inches(col_width)

        # Phase H: header & row colors depend on dark mode
        if self._dark_mode:
            header_fill = self._darken(self.theme.title_slide_background, 1.15)
            header_text = "#FFFFFF"
            even_bg = self._darken(self.theme.title_slide_background, 1.05)
            odd_bg = self._darken(self.theme.title_slide_background, 0.9)
            row_text = "#FFFFFFCC"
        else:
            header_fill = self.theme.accent_primary
            header_text = self.theme.background
            even_bg = self.theme.card_bg
            odd_bg = self.theme.background
            row_text = self.theme.text_primary

        # Format headers
        for c_idx, head in enumerate(headers):
            cell = table.cell(0, c_idx)
            cell.text = head
            cell.fill.solid()
            cell.fill.fore_color.rgb = hex_to_rgb(header_fill)

            for p in cell.text_frame.paragraphs:
                p.font.name = self.settings.typography.header_font
                p.font.size = Pt(14)
                p.font.bold = True
                p.font.color.rgb = hex_to_rgb(header_text)

        # Format rows with alternate zebra styling
        for r_idx, row in enumerate(rows):
            bg_color = even_bg if r_idx % 2 == 0 else odd_bg
            for c_idx, val in enumerate(row):
                cell = table.cell(r_idx + 1, c_idx)
                cell.text = str(val)
                cell.fill.solid()
                cell.fill.fore_color.rgb = hex_to_rgb(bg_color)

                for p in cell.text_frame.paragraphs:
                    p.font.name = self.settings.typography.body_font
                    p.font.size = Pt(12)
                    p.font.color.rgb = hex_to_rgb(row_text)

        # Render insight caption below table as filled box (Phase C)
        if render_insight:
            self._add_insight_box(
                slide, insight,
                left, table_top + table_h + 0.05, width, insight_h
            )

    # ── Phase C helpers: eyebrow, footer, insight boxes ───────────────────────────
    def _add_insight_box(
        self, slide, text: str, left: float, top: float, width: float, height: float
    ):
        """Draw a filled rectangle behind an insight/callout caption (Phase C)."""
        # Phase H: dark-aware insight box
        if self._dark_mode:
            insight_bg = self._darken(self.theme.title_slide_background, 1.15)
            text_color = "#FFFFFFCC"
        else:
            insight_bg = getattr(self.theme, 'insight_box_bg', self.theme.accent_quaternary) or self.theme.accent_quaternary
            text_color = self.theme.text_primary
        shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = hex_to_rgb(insight_bg)
        shape.line.fill.background()
        
        tx = slide.shapes.add_textbox(Inches(left + 0.06), Inches(top + 0.03), Inches(width - 0.12), Inches(height - 0.06))
        tf = tx.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.0)
        tf.text = text
        p = tf.paragraphs[0]
        p.font.name = self.settings.typography.body_font
        p.font.size = Pt(10)  # Reduced from 14pt for a more premium, compact look
        p.font.italic = True
        p.font.color.rgb = hex_to_rgb(text_color)

    def _render_eyebrow_widget(self, slide, payload, left: float, top: float, width: float, height: float):
        """Render an uppercase letter-spaced eyebrow label (Phase C+H)."""
        text = str(payload.get("text", ""))
        # Eyebrow color: gold on dark, gold on light — same accent_secondary
        eyebrow_color = getattr(self.theme, 'eyebrow_color', self.theme.accent_secondary) or self.theme.accent_secondary
        tx = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        tf = tx.text_frame
        tf.text = text.upper()
        p = tf.paragraphs[0]
        p.font.name = self.settings.typography.body_font
        p.font.size = Pt(14)
        p.font.italic = False
        p.font.color.rgb = hex_to_rgb(eyebrow_color)
        # Phase H: add letter-spacing via XML (python-pptx doesn't expose it directly)
        try:
            rPr = p._p.get_or_add_rPr()
            rPr.set('spc', str(int(400)))  # 400 hundredths of a point = 4pt spacing
        except Exception:
            pass

    def _render_footer_widget(self, slide, payload, left: float, top: float, width: float, height: float):
        """Render a muted footer line at bottom of title/closing slides (Phase C+H)."""
        text = str(payload.get("text", ""))
        footer_color = getattr(self.theme, 'footer_color', self.theme.text_secondary) or self.theme.text_secondary
        # Phase H: on dark slides, ensure footer is visible
        if self._dark_mode:
            footer_color = "#FFFFFFAA"
        tx = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        tf = tx.text_frame
        tf.text = text
        p = tf.paragraphs[0]
        p.font.name = self.settings.typography.body_font
        p.font.size = Pt(9.0)
        p.font.color.rgb = hex_to_rgb(footer_color)
