import logging
from typing import Dict, Any
from ppt_gen.core.blueprint_library import Blueprint
from ppt_gen.core.layout_engine import LayoutEngine

logger = logging.getLogger("validator")


def _iter_text_fields(payload: Any):
    """Yield string values from known text-bearing fields in a slot payload dict."""
    if not isinstance(payload, dict):
        return
    for key in ("text", "title", "desc", "badge", "label", "value"):
        val = payload.get(key)
        if isinstance(val, str) and val:
            yield key, val


def validate_deck(deck_plan, blueprints: Dict[str, Blueprint], layout_engine: LayoutEngine) -> bool:
    """
    Pre-render validation pass over a compiled FullDeckPlan.

    Checks (in order of severity):
      1. Unknown archetypes — ERROR.
      2. Out-of-bounds grid areas — ERROR (slot extends past the declared grid).
      3. Group-background padding collisions — ERROR (card backgrounds physically overlap).
      4. Text-length constraints — WARNING (AutoFit handles display; reported for awareness).
      5. max_items violations — ERROR (too many data rows for a fixed table slot).

    Does NOT modify any content.  AutoFit in the renderer handles visual text overflow.
    Returns True when no ERRORs are found (warnings are non-blocking).
    """
    has_errors = False
    total_warnings = 0
    slide_list = deck_plan.slides          # List[ResolvedSlide]

    for slide_idx, slide in enumerate(slide_list):
        label = f"Slide {slide_idx + 1} ({slide.archetype})"

        blueprint = blueprints.get(slide.archetype)
        if not blueprint:
            logger.error(f"{label}: Unknown archetype — cannot validate.")
            has_errors = True
            continue

        grid_cols, grid_rows = blueprint.grid  # default (12, 8)

        # ── 1. Out-of-bounds + group collection ──────────────────────────────
        groups: Dict[str, list] = {}
        for slot in blueprint.slots:
            c, r, w, h = slot.grid_area

            if c < 0 or c + w > grid_cols + 0.01:
                logger.error(
                    f"{label}: Slot '{slot.id}' exceeds horizontal bounds "
                    f"({c:.2f}+{w:.2f}={c+w:.2f} > {grid_cols})"
                )
                has_errors = True

            if r < 0 or r + h > grid_rows + 0.01:
                logger.error(
                    f"{label}: Slot '{slot.id}' exceeds vertical bounds "
                    f"({r:.2f}+{h:.2f}={r+h:.2f} > {grid_rows})"
                )
                has_errors = True

            if slot.group:
                groups.setdefault(slot.group, []).append(slot)

        # ── 2. Group-background padding collision detection ───────────────────
        group_list = list(groups.items())
        for i in range(len(group_list)):
            for j in range(i + 1, len(group_list)):
                g1_name, g1_slots = group_list[i]
                g2_name, g2_slots = group_list[j]

                l1, t1, w1, h1 = layout_engine.get_group_rect_in_inches(g1_slots)
                l2, t2, w2, h2 = layout_engine.get_group_rect_in_inches(g2_slots)

                # Positive overlap on both axes → collision (0.01 in tolerance)
                x_overlap = min(l1 + w1, l2 + w2) - max(l1, l2)
                y_overlap = min(t1 + h1, t2 + h2) - max(t1, t2)
                if x_overlap > 0.01 and y_overlap > 0.01:
                    logger.error(
                        f"{label}: Group card collision — '{g1_name}' ↔ '{g2_name}' "
                        f"overlap {x_overlap:.3f}\" H × {y_overlap:.3f}\" V (including padding)."
                    )
                    has_errors = True

        # ── 3. Text-length & row-count constraints ────────────────────────────
        for slot in blueprint.slots:
            payload = slide.slots.get(slot.id) or {}

            if slot.max_chars:
                for field_name, text_val in _iter_text_fields(payload):
                    if len(text_val) > slot.max_chars:
                        logger.warning(
                            f"{label}: Slot '{slot.id}' field '{field_name}' is "
                            f"{len(text_val)} chars (max {slot.max_chars}). "
                            "AutoFit will handle display."
                        )
                        total_warnings += 1

            if slot.max_items:
                rows = payload.get("rows") if isinstance(payload, dict) else None
                if rows and len(rows) > slot.max_items:
                    logger.error(
                        f"{label}: Slot '{slot.id}' has {len(rows)} rows "
                        f"(max_items={slot.max_items})."
                    )
                    has_errors = True

    # ── Summary ───────────────────────────────────────────────────────────────
    if has_errors:
        logger.warning(
            f"Validation complete — ERRORS found. "
            f"AutoFit may mitigate text issues; layout bugs require blueprint fixes."
        )
    else:
        logger.info(
            f"Validation passed — {total_warnings} warning(s), 0 errors."
        )

    return not has_errors
