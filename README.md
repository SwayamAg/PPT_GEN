# ppt-gen: McKinsey-Style Slide Deck Generator

A template-driven PowerPoint generation engine combining an LLM-powered content filler (using local Gemma 4 / Ollama) with a deterministic synthetic data engine, exact typography measuring, and styled chart rendering.

## 🚀 Key Features

* **LLM-Enforced Dynamic Schemas**: Uses Pydantic models to construct runtime slot schemas, ensuring local LLMs (like `gemma4:e4b`) output clean, validated content structures.
* **Deterministic Synthetic Data Engine**: Avoids letting the LLM invent raw numeric values (which leads to statistical inconsistencies). Instead, numbers, trendlines, and metrics are calculated deterministically using a keyword-based direction inference and a stable seeded RNG.
* **Human-in-the-Loop Outline Checkpoint**: Pauses execution after high-level planning to export a `temp_outline.md`. You can review, rename, or swap archetypes in any text editor before slide rendering begins.
* **Typographic Overflow Audits**: Uses Pillow's `ImageFont` metrics to binary-search font sizes down at render-time, wrapping text cleanly and placing ellipses when a line exceeds its boundary box.
* **Fast Re-render Loop**: Separates LLM planning/writing from physical compilation. Generates a `<name>.plan.json` containing slide metadata and resolved values. You can update metrics in the JSON file and compile slide modifications in sub-second time without calling the LLM.

---

## 🛠️ Architecture Overview

```
┌─────────────┐   ┌──────────────────┐   ┌───────────────────┐
│ Config Layer │→ │ Requirements     │→ │ Preset Presets /  │
│ (TOML)      │   │ Wizard (CLI QA)  │   │ Planner (LLM x2)  │
└─────────────┘   └──────────────────┘   └─────────┬─────────┘
                                                   ▼
                                     ┌─────────────────────────┐
                                     │ OUTLINE REVIEW CHECK    │
                                     │ (human edits & saves)   │
                                     └─────────────┬───────────┘
                                                   ▼
                           ┌───────────────────────────────────┐
                           │ Per-Slide Loop:                   │
                           │ Blueprint (grid) → Generator (LLM)│
                           │ → Truncation → Sizing → Matplotlib│
                           └───────────────────┬───────────────┘
                                               ▼
                                     ┌───────────────────┐
                                     │ Renderer (.pptx)  │
                                     └───────────────────┘
```

---

## 📥 Setup Instructions

### 1. Prerequisites
* **Python**: 3.10 or higher
* **Ollama**: Local server running with your target model installed (e.g., `gemma4:e4b`).

### 2. Installation
Clone the repository, initialize your virtual environment, and install dependencies:

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Windows (CMD)
.\venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Ollama parameters, default fonts, and grid divisions are specified in `ppt_gen/config/config.toml`:

```toml
[llm]
host = "http://localhost:11434"
model = "gemma4:e4b" # Registered name in Ollama list
default_temperature = 0.3
```

Theme color hex values are customized separately inside `ppt_gen/themes/light.toml` and `dark.toml`.

---

## 📖 Usage Guide

The CLI supports two primary commands: `build` (to create new presentations) and `render` (to update slides using a plan file).

### 1. Generating a Slide Deck
Run the build command with a topic prompt.

```powershell
# Guided interactive generation:
python cli.py build "Establish pricing structure and channel partners for expansion tier"

# Fast generation (skips wizard & review checkpoints, using consulting presets):
python cli.py build "Margin recovery strategy for retail premium tier" --fast
```

* **Interactive Flow**: The wizard collects audience, theme, and optional numbers. A review outline will export to `output/outline_review.md`. Open and modify slides, save, and confirm in the terminal to compile.
* **Output**: Writes the widescreen PowerPoint (`.pptx`) and sidecar metadata (`.plan.json`) to the `output/` directory.

### 2. Fast Edit & Re-render Loop (LLM-Free)
If you want to plug in real values or modify copy post-generation:

1. Open the generated `output/your_deck_name.plan.json` in a text editor.
2. Edit numbers or string slots directly. For example:
   ```json
   "stat1": {
     "label": "Margin recovery in retail segments",
     "value": "↑ 45%"
   }
   ```
3. Run the render sub-command pointing to the file to regenerate the slides instantly:
   ```powershell
   python cli.py render output/your_deck_name.plan.json
   ```
   *This regenerates transparent chart PNGs, rescales typography, compiles tables, and saves to the target `.pptx` file.*
