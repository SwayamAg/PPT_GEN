import logging
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

from ppt_gen.core.settings import Settings
from ppt_gen.core.blueprint_library import get_blueprint
from ppt_gen.core.plan_store import FullDeckPlan
from ppt_gen.core.layout_engine import LayoutEngine
from ppt_gen.core.overflow import audit_text_fit
from ppt_gen.core.chart_engine import render_chart

logger = logging.getLogger("renderer")

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
            
            # Set background color
            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = hex_to_rgb(self.theme.background)
            
            # Retrieve blueprint rules
            blueprint = get_blueprint(r_slide.archetype)
            slots_map = {s.id: s for s in blueprint.slots}
            
            # Step 1: Render group container card background boxes
            unique_groups = set(s.group for s in blueprint.slots if s.group)
            for group_id in unique_groups:
                group_slots = [s for s in blueprint.slots if s.group == group_id]
                # Calculate combined bounding box
                left, top, width, height = self.layout_engine.get_group_rect_in_inches(group_slots)
                
                # Draw visual container card
                card_shape = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
                )
                card_shape.fill.solid()
                card_shape.fill.fore_color.rgb = hex_to_rgb(self.theme.card_bg)
                
                # If this is the challenge box in 'title_challenge', style with accent tint and no borders
                if group_id == "challenge_box":
                    card_shape.line.color.rgb = hex_to_rgb(self.theme.accent_quaternary)
                    card_shape.fill.fore_color.rgb = hex_to_rgb(self.theme.accent_quaternary)
                else:
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
                    
        # Save output presentation
        output_pptx_path.parent.mkdir(exist_ok=True, parents=True)
        prs.save(str(output_pptx_path))
        logger.info(f"Presentation saved successfully to {output_pptx_path}")

    def _render_text_widget(self, slide, slot, payload, left, top, width, height):
        text = payload.get("text", "")
        if not text:
            return
            
        # Is it slide header?
        is_header = (slot.id == "title")
        opt_size, lines = audit_text_fit(text, width, height, self.settings, is_header)
        
        tx_box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.02)
        
        # Render line-by-line
        p = tf.paragraphs[0]
        p.text = lines[0]
        p.font.name = self.settings.typography.header_font if is_header else self.settings.typography.body_font
        p.font.size = Pt(opt_size)
        p.font.bold = is_header
        p.font.color.rgb = hex_to_rgb(self.theme.accent_primary if is_header else self.theme.text_primary)
        
        for line in lines[1:]:
            p2 = tf.add_paragraph()
            p2.text = line
            p2.font.name = self.settings.typography.body_font
            p2.font.size = Pt(opt_size)
            p2.font.color.rgb = hex_to_rgb(self.theme.text_primary)
            # If it has list max items, format with standard bullet points
            if slot.max_items:
                p2.level = 0

    def _render_stat_widget(self, slide, slot, payload, left, top, width, height):
        value = payload.get("value", "")
        label = payload.get("label", "")
        
        tx_box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.04)
        
        if slot.widget == "stat_callout":
            # Stat callout: Value on top (big), Label below
            p1 = tf.paragraphs[0]
            p1.text = value
            p1.font.name = self.settings.typography.header_font
            p1.font.size = Pt(28)
            p1.font.bold = True
            p1.font.color.rgb = hex_to_rgb(self.theme.accent_primary)
            
            p2 = tf.add_paragraph()
            p2.text = label
            p2.font.name = self.settings.typography.body_font
            p2.font.size = Pt(9.5)
            p2.font.color.rgb = hex_to_rgb(self.theme.text_secondary)
        else:
            # KPI pill: value and label inline
            p1 = tf.paragraphs[0]
            p1.text = f"{value}  —  {label}" if value else label
            p1.font.name = self.settings.typography.body_font
            p1.font.size = Pt(10)
            p1.font.bold = True
            p1.font.color.rgb = hex_to_rgb(self.theme.text_primary)

    def _render_step_widget(self, slide, slot, payload, left, top, width, height):
        badge = payload.get("badge", "")
        title = payload.get("title", "")
        desc = payload.get("desc", "")
        
        tx_box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Inches(0.04)
        
        # Paragraph 1: Badge + Title
        p1 = tf.paragraphs[0]
        p1.text = f"{badge}  {title}" if badge else title
        p1.font.name = self.settings.typography.header_font
        p1.font.size = Pt(11)
        p1.font.bold = True
        p1.font.color.rgb = hex_to_rgb(self.theme.accent_primary)
        
        # Paragraph 2: Description
        if desc:
            p2 = tf.add_paragraph()
            p2.text = desc
            p2.font.name = self.settings.typography.body_font
            p2.font.size = Pt(9.5)
            p2.font.color.rgb = hex_to_rgb(self.theme.text_secondary)

    def _render_chart_widget(self, slide, slide_idx, slot, payload, left, top, width, height):
        title = payload.get("title", "")
        insight = payload.get("insight_caption", "")
        chart_data = payload.get("chart_data", {})
        chart_type = payload.get("chart_type", "line")
        
        title_h = 0.4
        insight_h = 0.4 if insight else 0.0
        
        # Title text box
        if title:
            tx_box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(title_h))
            p = tx_box.text_frame.paragraphs[0]
            p.text = title
            p.font.name = self.settings.typography.header_font
            p.font.size = Pt(11)
            p.font.bold = True
            p.font.color.rgb = hex_to_rgb(self.theme.text_primary)
            
        # Draw matplotlib graphic
        chart_w = width - 0.2
        chart_h = height - title_h - insight_h - 0.1
        
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
        
        # Embed chart image
        if chart_path.exists():
            slide.shapes.add_picture(
                str(chart_path),
                Inches(left + 0.1),
                Inches(top + title_h),
                Inches(chart_w),
                Inches(chart_h)
            )
            
        # Insight caption text box
        if insight:
            tx_box_cap = slide.shapes.add_textbox(
                Inches(left), Inches(top + title_h + chart_h + 0.05), Inches(width), Inches(insight_h)
            )
            p_cap = tx_box_cap.text_frame.paragraphs[0]
            p_cap.text = insight
            p_cap.font.name = self.settings.typography.body_font
            p_cap.font.size = Pt(9.0)
            p_cap.font.italic = True
            p_cap.font.color.rgb = hex_to_rgb(self.theme.text_secondary)

    def _render_table_widget(self, slide, slot, payload, left, top, width, height):
        title = payload.get("title", "")
        insight = payload.get("insight_caption", "")
        headers = payload.get("headers", [])
        rows = payload.get("rows", [])
        
        title_h = 0.4
        insight_h = 0.4 if insight else 0.0
        
        if title:
            tx_box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(title_h))
            p = tx_box.text_frame.paragraphs[0]
            p.text = title
            p.font.name = self.settings.typography.header_font
            p.font.size = Pt(11)
            p.font.bold = True
            p.font.color.rgb = hex_to_rgb(self.theme.text_primary)
            
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
            
        # Format headers
        for c_idx, head in enumerate(headers):
            cell = table.cell(0, c_idx)
            cell.text = head
            cell.fill.solid()
            cell.fill.fore_color.rgb = hex_to_rgb(self.theme.accent_primary)
            
            # Style header paragraphs
            for p in cell.text_frame.paragraphs:
                p.font.name = self.settings.typography.header_font
                p.font.size = Pt(9.5)
                p.font.bold = True
                p.font.color.rgb = hex_to_rgb(self.theme.background)  # Text matches screen bg
                
        # Format rows with alternate zebra styling
        for r_idx, row in enumerate(rows):
            bg_color = self.theme.card_bg if r_idx % 2 == 0 else self.theme.background
            for c_idx, val in enumerate(row):
                cell = table.cell(r_idx + 1, c_idx)
                cell.text = str(val)
                cell.fill.solid()
                cell.fill.fore_color.rgb = hex_to_rgb(bg_color)
                
                # Style cell paragraphs
                for p in cell.text_frame.paragraphs:
                    p.font.name = self.settings.typography.body_font
                    p.font.size = Pt(9.0)
                    p.font.color.rgb = hex_to_rgb(self.theme.text_primary)
                    
        # Render insight caption below table
        if insight:
            tx_box_cap = slide.shapes.add_textbox(
                Inches(left), Inches(table_top + table_h + 0.05), Inches(width), Inches(insight_h)
            )
            p_cap = tx_box_cap.text_frame.paragraphs[0]
            p_cap.text = insight
            p_cap.font.name = self.settings.typography.body_font
            p_cap.font.size = Pt(9.0)
            p_cap.font.italic = True
            p_cap.font.color.rgb = hex_to_rgb(self.theme.text_secondary)
