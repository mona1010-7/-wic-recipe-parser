# WIC Recipe Parser

WIC Recipe Parser is a Streamlit app that turns ordinary recipes into WIC-friendly meal plans. It parses ingredients, checks WIC eligibility against a local food ontology, suggests substitutions with an AI model, rewrites the recipe, and exports a shopping list or recipe card.

## Features

- Paste a recipe or load a family-friendly example.
- Parse ingredients into structured data.
- Check ingredients against a local WIC food database.
- Suggest WIC-friendly substitutions using Featherless.ai's OpenAI-compatible API.
- Rewrite the full recipe with adapted ingredients.
- Group the shopping list by Produce, Dairy, Grains, Proteins, and Other.
- Scale servings without re-calling the API.
- Translate output to Spanish.
- Upload text, PDF, or image recipes.
- Export a text recipe card or PDF.

## Tech Stack

- Python
- Streamlit
- Featherless.ai
- OpenAI-compatible chat completions
- Qwen2.5 Instruct models
- Local fuzzy matching and WIC ontology
- fpdf2, pypdf, Pillow, and pytesseract

## Run Locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Add your Featherless API key:

```bash
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then edit `.streamlit/secrets.toml`:

```toml
FEATHERLESS_API_KEY = "your-real-key"
```

3. Start the app:

```bash
streamlit run app.py
```

Image OCR uses Tesseract. On Streamlit Community Cloud, `packages.txt` installs `tesseract-ocr`. Locally, install Tesseract separately if you want image OCR; PDF text extraction works through Python dependencies.

## Deploy On Streamlit Community Cloud

Use these settings:

- Repository: `mona1010-7/-wic-recipe-parser`
- Branch: `main`
- Main file path: `app.py`

In the app's Streamlit Cloud settings, add this secret:

```toml
FEATHERLESS_API_KEY = "your-real-key"
```

## Project Files

- `app.py`: Streamlit UI, AI orchestration, parsing, rewriting, exports, and session state.
- `wic_database.py`: WIC food ontology, state notes, substitutions, and confidence helpers.
- `requirements.txt`: Python dependencies for Streamlit Cloud.
- `packages.txt`: System package needed for image OCR.
- `DEVPOST_SUBMISSION.md`: Copy-paste Devpost project page content.
