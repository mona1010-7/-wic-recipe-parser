# Devpost Submission Draft

## Project Story

# WIC Recipe Parser

## The Inspiration

Every week, millions of families walk into grocery stores with WIC benefits and walk out still unsure how to turn those benefits into meals. WIC provides crucial nutrition assistance, but the gap is that WIC helps people shop, not cook.

Existing tools can tell a family what is eligible at checkout. But when someone finds a recipe that calls for butter, all-purpose flour, or heavy cream, they still need to know which ingredients are covered, what to swap, and how to rewrite the recipe without losing the meal. WIC Recipe Parser was built to close the gap between the grocery store and the kitchen table.

## What It Does

WIC Recipe Parser is an AI-powered tool that transforms any recipe into a WIC-friendly version:

1. Paste any recipe or load an example.
2. Parse ingredients with structured NLP extraction.
3. Check eligibility against a local WIC food ontology.
4. Suggest WIC-approved substitutions with explanations.
5. Rewrite the full recipe with step-by-step instructions.
6. Generate a shopping list grouped by category.
7. Scale servings for different family sizes.
8. Translate the output to Spanish.
9. Export a clean recipe card or PDF.

## How I Built It

The system uses a hybrid local and cloud AI architecture:

```text
Recipe input -> Featherless Qwen model -> Structured JSON -> Local WIC matching -> Substitutions and recipe rewrite
```

- Local layer: Python fuzzy matching against a hardcoded WIC food database for fast, no-cost eligibility checks.
- AI layer: Featherless.ai's OpenAI-compatible API with Qwen instruct models for parsing, substitution reasoning, translation, and recipe rewriting.
- Streamlit layer: Interactive recipe input, WIC controls, session-state caching, shopping lists, and exports.

## Tech Stack

| Layer | Tool |
| --- | --- |
| Frontend | Streamlit |
| Language | Python |
| AI provider | Featherless.ai |
| AI models | Qwen2.5 Instruct models |
| API style | OpenAI-compatible chat completions |
| NLP | Structured JSON extraction and entity linking |
| Database | Hardcoded WIC ontology based on federal guidelines |
| Documents | fpdf2, pypdf |
| OCR | Pillow, pytesseract, Tesseract OCR |
| Deployment | Streamlit Community Cloud |
| Editor | Cursor and Codex |

## Challenges I Faced

### Original Ingredient JSON Bug

The first substitution prompt asked the model to return JSON, but the model sometimes returned placeholder keys instead of exact ingredient names. That broke the parser because the app could not match substitutions back to the original ingredients.

Fix: I rewrote the prompt so the keys must be the exact original ingredient names and added JSON cleanup to handle model output safely.

### Duplicate Streamlit Keys

Repeated items in the shopping list caused duplicate widget key crashes.

Fix: I switched checkbox keys to stable category and index-based keys.

### API Latency During Demo

Large models can take several seconds per call, which is risky in a live demo.

Fix: I used `st.session_state` caching so parsed ingredients, substitutions, and rewrites are reused when the user changes local controls like servings.

### No Central WIC API

There is no single public federal API that gives real-time WIC eligibility across every state.

Fix: I built an MVP around a local WIC ontology, state notes, and clear reminders that rules can vary by WIC office.

## What I Learned

- Constrained generation is different from chat: valid JSON requires specific prompts, lower temperatures, and fallback handling.
- Hybrid systems are practical: local matching handles deterministic checks while the LLM handles language-heavy reasoning.
- Streamlit session state is essential because the script reruns on every interaction.
- Accessibility features like Spanish translation can make a small tool useful to many more families.

## What's Next

- Add deeper state-specific WIC databases.
- Improve image and PDF OCR for cookbook pages.
- Integrate nutrition APIs for side-by-side nutrition facts.
- Add voice input for low-literacy or hands-free use.
- Add a monthly WIC allotment tracker.

## Impact

WIC Recipe Parser helps families turn benefits into realistic meals. By adapting recipes into benefits-friendly meal plans, it can reduce food waste, stretch grocery budgets, and make healthy cooking more accessible.

## Built With

Use these tags on Devpost:

```text
Python
Streamlit
Featherless.ai
OpenAI API
Qwen
JSON
NLP
OCR
Tesseract
Pillow
pypdf
fpdf2
Streamlit Community Cloud
Cursor
Codex
```

## Try It Out Links

- Source code: https://github.com/mona1010-7/-wic-recipe-parser
- Demo app: add your Streamlit Community Cloud URL after deployment.

## Project Media Checklist

- Screenshot of the recipe input and controls.
- Screenshot of the WIC eligibility analysis tab.
- Screenshot of the before/after recipe transformation.
- Screenshot of the shopping list and export tab.
- Short demo video showing paste recipe -> analyze -> export.
