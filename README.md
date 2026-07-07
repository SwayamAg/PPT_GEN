# ppt-gen: McKinsey-Style Slide Deck Generator

A template-driven PowerPoint generation engine combining a local LLM content filler (Gemma 4 via Ollama) with a deterministic synthetic data engine, pixel-accurate typography measuring, and branded Matplotlib chart rendering.

---

## 🚀 Key Features

- **LLM-Enforced Dynamic Schemas** — Pydantic models are built at runtime per archetype, ensuring local LLMs output clean, schema-validated slot content.
- **Deterministic Synthetic Data Engine** — LLMs never invent raw numbers. A seeded RNG engine generates direction-coherent stats, trendlines, and tables from keyword inference on the label text.
- **Human-in-the-Loop Outline Checkpoint** — After planning, an editable `output/outline_review.md` is created. Review, rename slides, or swap archetypes before generation starts. Skip with `--fast`.
- **Pixel-Accurate Typography** — Uses `Pillow` + system TTF fonts to binary-search font sizes and word-wrap text to fit exactly within each slide box — no overflow, no shrink-to-illegible.
- **Fast Re-render Loop** — LLM content and final rendering are fully decoupled. Edit numbers in the sidecar `<name>.plan.json` and recompile to `.pptx` in under a second with no LLM call.
- **6 Slide Archetypes** — `title_challenge`, `comparison_bars`, `two_column_initiative`, `single_chart_focus`, `stat_grid_charts`, `table_priorities`.
- **4 Chart Types** — Horizontal ranked bar, grouped comparison bar, smooth trend line, multi-subplot bar — each with hardcoded brand styling.

---

## 🛠️ Architecture Overview

```
┌─────────────┐   ┌──────────────────┐   ┌────────────────────────┐
│ Config TOML │→  │ Requirements     │→  │ Preset Templates  /    │
│ + Themes    │   │ Wizard (CLI Q&A) │   │ Deck & Section Planner │
└─────────────┘   └──────────────────┘   │ (LLM #1 & #2)         │
                                          └──────────┬─────────────┘
                                                     ▼
                                       ┌─────────────────────────────┐
                                       │ OUTLINE REVIEW CHECKPOINT   │
                                       │  output/outline_review.md   │
                                       │ (human edits → confirm)     │
                                       └─────────────┬───────────────┘
                                                     ▼
                           ┌─────────────────────────────────────────┐
                           │ Per-Slide Loop (LLM #3 per slide):      │
                           │ Blueprint → Slide Generator → Formatter  │
                           │ → Synthetic Data Engine → Layout Engine  │
                           │ → Typography Audit → Chart Engine        │
                           └──────────────────────┬──────────────────┘
                                                  ▼
                                    ┌─────────────────────────┐
                                    │ plan.json  +  .pptx     │
                                    │ (Renderer via python-pptx)│
                                    └─────────────────────────┘
```

---

## 📥 Setup

### Prerequisites
- **Python** 3.10 or higher
- **Ollama** running locally with your target model pulled (e.g. `gemma4:e4b`)

### Installation

```powershell
# Clone
git clone https://github.com/SwayamAg/PPT_GEN.git
cd PPT_GEN

# Create & activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1          # PowerShell
# or: .\venv\Scripts\activate.bat    # CMD

# Install dependencies
pip install -r requirements.txt

# Verify setup
python tests/test_ppt_gen.py         # should print: Ran 5 tests ... OK
```

---

## ⚙️ Configuration

All settings live in `ppt_gen/config/config.toml`:

```toml
[llm]
host  = "http://localhost:11434"
model = "gemma4:e4b"          # must match `ollama list` name exactly
default_temperature = 0.3
plan_temperature    = 0.5
max_retries         = 2       # auto-repair attempts on bad JSON

[presentation]
width_inches  = 13.33         # widescreen 16:9
height_inches = 7.5
grid_cols = 12
grid_rows = 8
```

Theme colors are in `ppt_gen/themes/light.toml` and `dark.toml`.

---

## 📖 CLI Reference

### `build` — Generate a new deck

```powershell
python cli.py build "PROMPT" [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `"PROMPT"` | positional | required | Topic, goal, or full description of the deck |
| `--fast` | flag | off | Skips the interactive Q&A wizard **and** the outline review checkpoint |
| `--mock` | flag | off | Bypasses Ollama entirely — uses hardcoded content (offline testing) |
| `--theme` | `light` / `dark` | `light` | Color palette applied to the whole deck |
| `--slides` | integer | `6` | Target slide count |

> **Note on `--slides`:** When a built-in preset is matched (e.g. `consulting_strategy`), the preset's fixed slide list is used. `--slides` only has effect when the LLM planners are invoked (i.e. `deck_type = "custom"` or no preset match).

**Examples:**

```powershell
# Interactive guided build with Gemma4:
python cli.py build "Market entry strategy for sustainable packaged foods in Tier-2 India"

# Fast build, dark theme, 3 slides:
python cli.py build "Pricing restructure for mid-market SaaS NRR recovery" --fast --slides 3 --theme dark

# Offline mock test:
python cli.py build "Any topic" --fast --mock
```

---

### `render` — Re-compile from an edited plan file

```powershell
python cli.py render output/your_deck_name.plan.json
```

No LLM calls — sub-second. Reads the `.plan.json`, rebuilds all chart PNGs, rescales typography, and overwrites the `.pptx`.

**Edit & re-render workflow:**
1. Open `output/<name>.plan.json` in any text editor.
2. Find a slot and change its value:
   ```json
   "stat1": { "label": "NRR recovery target", "value": "↑ 45%" }
   ```
3. Run `render` — the updated deck appears instantly.

---

## 📁 Project Structure

```
ppt_gen/
  config/config.toml          ← grid, LLM, typography settings
  themes/light.toml           ← light palette
  themes/dark.toml            ← dark palette
  core/
    settings.py               ← Pydantic config loader
    llm_client.py             ← Ollama wrapper + repair loop + mock
    requirements_wizard.py    ← interactive CLI Q&A
    deck_templates.py         ← built-in preset outlines
    deck_planner.py           ← LLM #1: objective + sections
    section_planner.py        ← LLM #2: slide titles + archetypes
    outline_checkpoint.py     ← human review of outline_review.md
    blueprint_library.py      ← 6 archetype grid definitions
    slide_generator.py        ← LLM #3: fill slots per slide
    content_parser.py         ← dynamic Pydantic slot models
    content_formatter.py      ← truncation + list clamping
    synthetic_data.py         ← deterministic number generator
    plan_store.py             ← compile / save / load plan.json
    layout_engine.py          ← grid → EMU inch coordinates
    overflow.py               ← text-fit audit interface
    typography.py             ← Pillow font sizing + word-wrap
    chart_engine.py           ← Matplotlib → transparent PNG
    renderer.py               ← python-pptx assembly + save
cli.py                        ← build / render CLI entrypoint
tests/test_ppt_gen.py         ← 5 unit tests
requirements.txt
```

---

## 🗂️ Output Files

Every build produces two files in `output/`:

| File | Purpose |
|---|---|
| `<slug>_<timestamp>.pptx` | Final widescreen PowerPoint presentation |
| `<slug>_<timestamp>.plan.json` | Editable sidecar — all resolved slot values tagged `synthetic` or `user_supplied` |

The `output/` directory is gitignored — generated files are never committed.
