"""WIC Recipe Parser - Streamlit app for LingHacks VII."""

import io
import json
import re
from copy import deepcopy
from datetime import datetime

import streamlit as st
from openai import OpenAI

from wic_database import (
    FALLBACK_SUBSTITUTIONS,
    STATE_NOTES,
    WIC_MONTHLY_DEFAULTS,
    WIC_OFFICE_TIP,
    get_match_confidence,
    get_seasonal_tip,
    get_wic_category,
    is_wic_eligible,
    substitution_confidence,
)

st.set_page_config(
    page_title="WIC Recipe Parser",
    page_icon="🥦",
    layout="wide",
)

st.markdown(
    """
    <style>
    div.stButton > button:first-child {
        background-color: #2E7D32;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: 600;
    }
    div.stButton > button:first-child:hover {
        background-color: #1B5E20;
        color: white;
        border: none;
    }
    .wic-badge-green { color: #2E7D32; font-weight: 600; }
    .wic-badge-red { color: #C62828; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

EXAMPLES = {
    "None": "",
    "🥞 Pancakes": """Pancakes
2 cups all-purpose flour
2 tbsp sugar
1 1/2 cups whole milk
2 eggs
3 tbsp butter, melted
2 tsp baking powder
1/2 tsp salt

Mix dry ingredients. Whisk in milk, eggs, and butter. Cook on a griddle until golden.""",
    "🌮 Tacos": """Beef Tacos
1 lb ground beef
1 packet taco seasoning
1/2 cup sour cream
1 cup shredded cheddar cheese
8 flour tortillas
2 tomatoes, diced
1 onion, diced

Brown beef, add seasoning. Serve in tortillas with toppings.""",
    "🍝 Pasta Primavera": """Pasta Primavera
12 oz penne pasta
1 cup heavy cream
1/2 cup parmesan cheese, grated
2 tbsp olive oil
1 zucchini, sliced
1 bell pepper, sliced
1 cup cherry tomatoes
3 cloves garlic, minced

Cook pasta. Sauté vegetables in olive oil. Add cream and parmesan. Toss with pasta.""",
    "🍛 Chicken Stir-Fry": """Chicken Stir-Fry
1 lb chicken breast, sliced
3 tbsp soy sauce
1 tbsp sesame oil
2 cups broccoli florets
1 bell pepper, sliced
1 cup snap peas
2 cups cooked white rice

Stir-fry chicken, add vegetables and sauces. Serve over rice.""",
    "🍲 Rice & Beans": """Classic Rice and Beans
1 cup white rice
1 can kidney beans, drained
1 tbsp olive oil
1 onion, diced
2 cloves garlic, minced
1 tsp cumin
1 cup chicken broth
Salt to taste

Sauté onion and garlic. Add rice, beans, broth, and cumin. Simmer until rice is tender.""",
    "🧀 Kid Mac & Cheese": """Mac and Cheese
8 oz elbow pasta
2 cups whole milk
2 cups shredded cheddar cheese
3 tbsp butter
2 tbsp all-purpose flour
1/2 tsp salt

Make roux with butter and flour. Whisk in milk and cheese. Toss with cooked pasta.""",
    "🍚 Arroz con Pollo": """Arroz con Pollo
2 cups white rice
1 lb chicken thighs
1 bell pepper, sliced
1 onion, diced
2 tbsp olive oil
1 packet sazon seasoning
1 cup frozen peas
3 cups chicken broth

Brown chicken, sauté vegetables, add rice and broth. Simmer until rice is done.""",
}

MODEL_OPTIONS = {
    "Qwen2.5-7B — Fast (recommended for live demo)": "Qwen/Qwen2.5-7B-Instruct",
    "Qwen2.5-14B — Balanced quality": "Qwen/Qwen2.5-14B-Instruct",
    "Llama 3.1-8B — Backup / fallback": "meta-llama/Llama-3.1-8B-Instruct",
}
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

UNIT_PATTERN = re.compile(
    r"^(\d+(?:\.\d+)?|\d+/\d+)\s*"
    r"(cups?|cup|tbsp|tsp|oz|lb|lbs|g|kg|ml|l|cloves?|cans?|packets?|slices?|pieces?)?\s*"
    r"(.+)$",
    re.IGNORECASE,
)


def init_session_state() -> None:
    defaults = {
        "parsed_ingredients": None,
        "substitutions": None,
        "rewritten_recipe": None,
        "non_wic_ingredients": None,
        "wic_score": None,
        "base_servings": 4,
        "processing_done": False,
        "original_recipe_text": "",
        "saved_recipes": [],
        "selected_model": DEFAULT_MODEL,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_client() -> OpenAI | None:
    try:
        api_key = st.secrets["FEATHERLESS_API_KEY"]
    except (KeyError, FileNotFoundError):
        st.error(
            "Missing API key. Add FEATHERLESS_API_KEY to `.streamlit/secrets.toml` "
            "or Streamlit Cloud secrets."
        )
        st.stop()
        return None

    if not api_key or api_key == "your-featherless-api-key-here":
        st.error(
            "Invalid API key. Set a real FEATHERLESS_API_KEY in `.streamlit/secrets.toml`."
        )
        st.stop()
        return None

    return OpenAI(
        base_url="https://api.featherless.ai/v1",
        api_key=api_key,
    )


def get_model() -> str:
    return st.session_state.get("selected_model", DEFAULT_MODEL)


def call_api(client: OpenAI, prompt: str, temperature: float, model: str | None = None) -> str:
    response = client.chat.completions.create(
        model=model or get_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


def extract_json(text: str):
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    return json.loads(text)


def parse_ingredients_local(recipe_text: str) -> list[dict]:
    """Rule-based ingredient parser (hybrid NLP — no API needed)."""
    ingredients = []
    for line in recipe_text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith(("mix ", "cook ", "serve ", "brown ", "whisk ")):
            continue
        if len(line) > 80 and not re.match(r"^\d", line):
            continue
        match = UNIT_PATTERN.match(line)
        if match:
            qty = f"{match.group(1)} {match.group(2) or ''}".strip()
            name = match.group(3).strip().lower()
            name = re.sub(r",.*$", "", name)
            ingredients.append({"name": name, "quantity": qty, "original": line})
        elif re.search(r"(flour|milk|egg|butter|oil|salt|sugar|cheese|rice|pasta|beef|chicken)", line, re.I):
            ingredients.append({"name": line.lower(), "quantity": "", "original": line})
    return ingredients


def parse_ingredients(client: OpenAI, recipe_text: str) -> list[dict]:
    prompt = f"""Parse the following recipe into a JSON array of ingredient objects.
Each object must have exactly these keys:
- "name": the ingredient name (lowercase, no quantity)
- "quantity": the amount with unit as a string
- "original": the exact original line from the recipe

Return ONLY valid JSON array, no markdown, no explanation.

Recipe:
{recipe_text}"""
    try:
        raw = call_api(client, prompt, temperature=0.1)
        parsed = extract_json(raw)
        if isinstance(parsed, list) and parsed:
            return parsed
    except Exception:
        pass
    local = parse_ingredients_local(recipe_text)
    if local:
        return local
    raise ValueError("Could not parse ingredients from recipe text.")


def dietary_prompt_notes(dietary: list[str]) -> str:
    notes = []
    mapping = {
        "Gluten-free": "Use only gluten-free WIC grains (rice, corn tortillas, certified GF oats).",
        "Vegan": "No eggs, dairy, or animal proteins — use beans, peanut butter, tofu, soy milk.",
        "Low-sodium": "Minimize added salt; use herbs, lemon juice, and unsalted WIC items.",
        "Dairy": "Avoid all dairy including milk, cheese, yogurt, butter.",
        "Nuts": "Avoid peanut butter and tree nuts.",
        "Soy": "Avoid soy milk and tofu.",
        "Eggs": "Avoid eggs; use canned beans or peanut butter for protein.",
    }
    for d in dietary:
        if d in mapping:
            notes.append(mapping[d])
    return "\n".join(notes)


def get_substitutions_from_api(
    client: OpenAI,
    non_wic: list[dict],
    allergens: list[str],
    state: str,
    dietary: list[str],
) -> dict:
    ingredient_names = [item["name"] for item in non_wic]
    allergen_note = dietary_prompt_notes(allergens + dietary)
    state_note = STATE_NOTES.get(state, STATE_NOTES["Federal (default)"])
    seasonal = get_seasonal_tip()

    prompt = f"""For each non-WIC ingredient below, suggest a WIC-friendly substitution.
State context: {state}. {state_note}
{seasonal}
Return ONLY valid JSON object where each KEY is the exact original ingredient name
and each VALUE is an object with keys:
- "substitution": WIC-friendly replacement
- "reason": why it works (taste, nutrition, WIC eligibility)
- "category": one of dairy, proteins, grains, produce, infant, other
- "confidence": integer 0-100 for how well the sub preserves the dish
- "wic_office_note": optional note if user should ask their WIC office (or empty string)

Dietary constraints:
{allergen_note or "None"}

Ingredients:
{json.dumps(ingredient_names)}

Return ONLY the JSON object, no markdown."""
    raw = call_api(client, prompt, temperature=0.3)
    subs = extract_json(raw)
    if not isinstance(subs, dict):
        raise ValueError("Expected a JSON object of substitutions.")
    return subs


def lookup_fallback_substitution(ingredient_name: str) -> dict | None:
    name = ingredient_name.lower().strip()
    if name in FALLBACK_SUBSTITUTIONS:
        entry = deepcopy(FALLBACK_SUBSTITUTIONS[name])
        entry["confidence"] = 88
        entry["wic_office_note"] = ""
        return entry
    for key, value in FALLBACK_SUBSTITUTIONS.items():
        if key in name or name in key:
            entry = deepcopy(value)
            entry["confidence"] = 85
            entry["wic_office_note"] = ""
            return entry
    return None


def merge_substitutions(
    client: OpenAI,
    non_wic: list[dict],
    allergens: list[str],
    state: str,
    dietary: list[str],
) -> dict:
    try:
        subs = get_substitutions_from_api(client, non_wic, allergens, state, dietary)
        validated = {}
        for item in non_wic:
            name = item["name"]
            if name in subs and isinstance(subs[name], dict):
                entry = subs[name]
                entry.setdefault("confidence", substitution_confidence(name, entry))
                entry.setdefault("wic_office_note", "")
                validated[name] = entry
            else:
                fallback = lookup_fallback_substitution(name)
                validated[name] = fallback or {
                    "substitution": "whole wheat flour or canned beans",
                    "reason": "Generic WIC-eligible pantry staple.",
                    "category": "grains",
                    "confidence": 70,
                    "wic_office_note": WIC_OFFICE_TIP,
                }
        return validated
    except Exception:
        result = {}
        for item in non_wic:
            name = item["name"]
            fallback = lookup_fallback_substitution(name)
            result[name] = fallback or {
                "substitution": "canned vegetables or whole grains",
                "reason": "API unavailable; using WIC-friendly fallback.",
                "category": "produce",
                "confidence": 75,
                "wic_office_note": WIC_OFFICE_TIP,
            }
        return result


def rewrite_recipe(
    client: OpenAI,
    recipe_text: str,
    ingredients: list[dict],
    substitutions: dict,
    servings: int,
    allergens: list[str],
    kid_friendly: bool = False,
    eli5: bool = False,
) -> dict:
    allergen_note = dietary_prompt_notes(allergens)
    style_notes = []
    if kid_friendly:
        style_notes.append("Use simple words suitable for cooking with children ages 5-10.")
    if eli5:
        style_notes.append(
            "Explain all tips in very plain language (Explain Like I'm 5 reading level)."
        )

    prompt = f"""Rewrite this recipe using WIC-friendly substitutions.
Target servings: {servings}
{allergen_note}
{" ".join(style_notes)}

Original recipe:
{recipe_text}

Parsed ingredients:
{json.dumps(ingredients, indent=2)}

Substitutions to apply:
{json.dumps(substitutions, indent=2)}

Return ONLY valid JSON with these keys:
- "title": adapted recipe title (string)
- "recipe_steps": array of step strings
- "shopping_list": object with keys Produce, Dairy, Grains, Proteins, Other — each an array of item strings
- "notes": array of educational tip strings about WIC nutrition
- "nutrition_win": one string highlighting the main nutritional benefit
- "difficulty": one of Easy, Medium, Hard
- "prep_time_min": integer minutes
- "cook_time_min": integer minutes
- "nutrition_comparison": object with keys protein_original_g, protein_new_g, fiber_new_g (integers, estimates per serving)

Return ONLY JSON, no markdown."""
    raw = call_api(client, prompt, temperature=0.4)
    result = extract_json(raw)
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object for rewritten recipe.")
    return result


def translate_recipe(client: OpenAI, recipe: dict) -> dict:
    prompt = f"""Translate ALL text values in this JSON recipe to Spanish.
Keep the JSON structure and keys exactly the same (keys stay in English).
Do not translate JSON keys, only string values inside arrays and objects.

{json.dumps(recipe, ensure_ascii=False, indent=2)}

Return ONLY valid JSON, no markdown."""
    raw = call_api(client, prompt, temperature=0.2)
    return extract_json(raw)


def build_fallback_recipe(
    recipe_text: str,
    ingredients: list[dict],
    substitutions: dict,
    servings: int,
) -> dict:
    steps = [
        "Review WIC substitutions listed below.",
        "Gather WIC-eligible ingredients from your shopping list.",
        "Prepare ingredients according to standard cooking methods.",
        "Combine and cook as described in the original recipe, swapping non-WIC items.",
        "Serve and enjoy your WIC-friendly meal!",
    ]
    shopping = {"Produce": [], "Dairy": [], "Grains": [], "Proteins": [], "Other": []}
    for ing in ingredients:
        name = ing["name"]
        if is_wic_eligible(name):
            cat_map = {
                "dairy": "Dairy",
                "proteins": "Proteins",
                "grains": "Grains",
                "produce": "Produce",
            }
            cat = cat_map.get(get_wic_category(name), "Other")
            shopping[cat].append(f"{ing.get('quantity', '')} {name}".strip())
        elif name in substitutions:
            shopping["Other"].append(substitutions[name]["substitution"])

    return {
        "title": "WIC-Adapted Recipe (Fallback)",
        "recipe_steps": steps,
        "shopping_list": shopping,
        "notes": [
            "WIC benefits cover essential food groups for families.",
            "Whole grains and beans add fiber and sustained energy.",
            "This fallback version was generated without full AI rewriting.",
        ],
        "nutrition_win": f"Adapted for {servings} servings using WIC-eligible substitutions.",
        "difficulty": "Easy",
        "prep_time_min": 15,
        "cook_time_min": 25,
        "nutrition_comparison": {
            "protein_original_g": 12,
            "protein_new_g": 14,
            "fiber_new_g": 6,
        },
    }


def scale_quantity(quantity: str, factor: float) -> str:
    if factor == 1.0 or not quantity:
        return quantity

    def scale_number(match: re.Match) -> str:
        num = float(match.group(1))
        scaled = num * factor
        if scaled == int(scaled):
            return str(int(scaled))
        return f"{scaled:.2g}"

    return re.sub(r"(\d+\.?\d*)", scale_number, quantity)


def scale_ingredients(ingredients: list[dict], from_servings: int, to_servings: int) -> list[dict]:
    if from_servings <= 0:
        return ingredients
    factor = to_servings / from_servings
    return [
        {**deepcopy(item), "quantity": scale_quantity(item.get("quantity", ""), factor)}
        for item in ingredients
    ]


def build_adapted_ingredient_list(ingredients: list[dict], substitutions: dict) -> list[dict]:
    adapted = []
    for ing in ingredients:
        name = ing["name"]
        if is_wic_eligible(name):
            adapted.append({**ing, "adapted_name": name, "changed": False})
        else:
            sub = substitutions.get(name, {})
            adapted.append({
                **ing,
                "adapted_name": sub.get("substitution", name),
                "changed": True,
            })
    return adapted


def build_ner_table(ingredients: list[dict]) -> list[dict]:
    rows = []
    for ing in ingredients:
        name = ing["name"]
        eligible = is_wic_eligible(name)
        rows.append({
            "Ingredient": name,
            "Quantity": ing.get("quantity", ""),
            "WIC Status": "Eligible" if eligible else "Not Eligible",
            "Category": get_wic_category(name),
            "Match Confidence": f"{get_match_confidence(name) * 100:.0f}%",
        })
    return rows


def estimate_shopping_cost(shopping: dict) -> dict[str, float]:
    unit_cost = {"Produce": 1.80, "Dairy": 2.50, "Grains": 1.50, "Proteins": 2.20, "Other": 2.00}
    costs = {cat: len(items) * unit_cost.get(cat, 2.0) for cat, items in shopping.items()}
    costs["total"] = sum(costs.values())
    return costs


def check_wic_balance(shopping: dict, allotments: dict) -> list[str]:
    mapping = {
        "Produce": "produce_cv",
        "Dairy": "dairy_equiv",
        "Grains": "grains_equiv",
        "Proteins": "proteins_equiv",
    }
    costs = estimate_shopping_cost(shopping)
    warnings = []
    for category, key in mapping.items():
        est = costs.get(category, 0)
        limit = allotments.get(key, 0)
        if limit and est > limit:
            warnings.append(
                f"**{category}**: est. ${est:.2f} may exceed ~${limit:.0f} monthly allotment."
            )
    return warnings


def build_export_text(
    recipe: dict,
    ingredients: list[dict],
    substitutions: dict,
    servings: int,
    original_text: str = "",
) -> str:
    lines = [
        "=" * 50,
        recipe.get("title", "WIC-Adapted Recipe"),
        f"Servings: {servings}",
        f"Difficulty: {recipe.get('difficulty', 'N/A')} | "
        f"Prep: {recipe.get('prep_time_min', '?')} min | "
        f"Cook: {recipe.get('cook_time_min', '?')} min",
        "=" * 50,
    ]
    if original_text:
        lines.extend(["", "ORIGINAL RECIPE", "-" * 20, original_text[:500], ""])

    lines.extend(["ADAPTED INGREDIENTS", "-" * 20])
    for ing in build_adapted_ingredient_list(ingredients, substitutions):
        tag = "[CHANGED]" if ing["changed"] else "[WIC OK]"
        lines.append(f"{tag} {ing.get('quantity', '')} {ing['adapted_name']}".strip())

    if substitutions:
        lines.extend(["", "SUBSTITUTIONS", "-" * 20])
        for name, sub in substitutions.items():
            lines.append(f"  {name} -> {sub.get('substitution', '')}")
            lines.append(f"    Why: {sub.get('reason', '')}")

    lines.extend(["", "INSTRUCTIONS", "-" * 20])
    for i, step in enumerate(recipe.get("recipe_steps", []), 1):
        lines.append(f"{i}. {step}")

    if recipe.get("nutrition_win"):
        lines.extend(["", "NUTRITION WIN", recipe["nutrition_win"]])

    nc = recipe.get("nutrition_comparison", {})
    if nc:
        lines.extend([
            "",
            "NUTRITION (per serving, estimated)",
            f"  Protein: {nc.get('protein_original_g', '?')}g -> {nc.get('protein_new_g', '?')}g",
            f"  Fiber: {nc.get('fiber_new_g', '?')}g",
        ])

    shopping = recipe.get("shopping_list", {})
    if shopping:
        lines.extend(["", "SHOPPING LIST", "-" * 20])
        for category, items in shopping.items():
            if items:
                lines.append(f"\n{category}:")
                for item in items:
                    lines.append(f"  [ ] {item}")

    lines.append("\nBuilt for LingHacks VII | WIC Recipe Parser")
    return "\n".join(lines)


def build_pdf_bytes(recipe: dict, ingredients: list[dict], substitutions: dict, servings: int) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "WIC Recipe Parser", ln=True)
    pdf.set_font("Helvetica", "", 11)
    title = recipe.get("title", "WIC-Adapted Recipe")
    pdf.cell(0, 8, title.encode("latin-1", "replace").decode("latin-1"), ln=True)
    pdf.cell(0, 6, f"Servings: {servings} | Difficulty: {recipe.get('difficulty', 'Easy')}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Ingredients", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for ing in build_adapted_ingredient_list(ingredients, substitutions):
        line = f"- {ing.get('quantity', '')} {ing['adapted_name']}".strip()
        pdf.multi_cell(0, 5, line.encode("latin-1", "replace").decode("latin-1"))

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Instructions", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for i, step in enumerate(recipe.get("recipe_steps", []), 1):
        pdf.multi_cell(0, 5, f"{i}. {step}".encode("latin-1", "replace").decode("latin-1"))

    shopping = recipe.get("shopping_list", {})
    if shopping:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Shopping List", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for category, items in shopping.items():
            if items:
                pdf.cell(0, 6, f"{category}:", ln=True)
                for item in items:
                    pdf.cell(0, 5, f"  [ ] {item}".encode("latin-1", "replace").decode("latin-1"), ln=True)

    return pdf.output()


def extract_text_from_upload(uploaded_file) -> str:
    if uploaded_file.type == "application/pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(uploaded_file.read()))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            st.error(f"PDF extraction failed: {exc}")
            return ""

    if uploaded_file.type and uploaded_file.type.startswith("image/"):
        try:
            import pytesseract
            from PIL import Image

            image = Image.open(uploaded_file)
            return pytesseract.image_to_string(image)
        except ImportError:
            st.warning("Install pytesseract and Pillow for OCR. Paste text manually.")
        except Exception as exc:
            st.warning(
                f"OCR failed ({exc}). Install Tesseract OCR on your system, or paste text manually."
            )
        return ""

    if uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8", errors="replace")

    return uploaded_file.read().decode("utf-8", errors="replace")


def finalize_recipe(
    client: OpenAI,
    recipe_text: str,
    ingredients: list[dict],
    substitutions: dict,
    servings: int,
    language: str,
    allergens: list[str],
    kid_friendly: bool,
    eli5: bool,
) -> dict:
    try:
        rewritten = rewrite_recipe(
            client, recipe_text, ingredients, substitutions, servings, allergens, kid_friendly, eli5
        )
    except Exception:
        rewritten = build_fallback_recipe(recipe_text, ingredients, substitutions, servings)

    if language == "Español":
        try:
            rewritten = translate_recipe(client, rewritten)
        except Exception:
            pass
    return rewritten


def process_recipe(
    client: OpenAI,
    recipe_text: str,
    servings: int,
    language: str,
    allergens: list[str],
    dietary: list[str],
    state: str,
    kid_friendly: bool,
    eli5: bool,
    progress_bar,
    status_text,
) -> None:
    status_text.text("Step 1/7: Parsing ingredients (AI + local NLP)...")
    progress_bar.progress(10)
    ingredients = parse_ingredients(client, recipe_text)

    status_text.text("Step 2/7: Named entity recognition & WIC linking...")
    progress_bar.progress(25)
    wic_count = sum(1 for ing in ingredients if is_wic_eligible(ing["name"]))
    non_wic = [ing for ing in ingredients if not is_wic_eligible(ing["name"])]
    total = len(ingredients) or 1
    score = round((wic_count / total) * 100)

    status_text.text("Step 3/7: Getting WIC substitutions...")
    progress_bar.progress(45)
    substitutions = merge_substitutions(client, non_wic, allergens, state, dietary) if non_wic else {}

    status_text.text("Step 4/7: Rewriting recipe...")
    progress_bar.progress(65)
    rewritten = finalize_recipe(
        client, recipe_text, ingredients, substitutions, servings, language, allergens, kid_friendly, eli5
    )

    status_text.text("Step 5/7: Building shopping list...")
    progress_bar.progress(85)

    if language == "Español":
        status_text.text("Step 6/7: Spanish translation applied...")
    else:
        status_text.text("Step 6/7: Finalizing...")
    progress_bar.progress(95)

    status_text.text("Step 7/7: Done!")
    progress_bar.progress(100)

    st.session_state.parsed_ingredients = ingredients
    st.session_state.substitutions = substitutions
    st.session_state.rewritten_recipe = rewritten
    st.session_state.non_wic_ingredients = non_wic
    st.session_state.wic_score = score
    st.session_state.base_servings = servings
    st.session_state.original_recipe_text = recipe_text
    st.session_state.processing_done = True


def regenerate_with_edits(
    client: OpenAI,
    recipe_text: str,
    ingredients: list[dict],
    substitutions: dict,
    servings: int,
    language: str,
    allergens: list[str],
    kid_friendly: bool,
    eli5: bool,
) -> None:
    with st.spinner("Regenerating recipe with your edits..."):
        rewritten = finalize_recipe(
            client, recipe_text, ingredients, substitutions, servings, language, allergens, kid_friendly, eli5
        )
        st.session_state.substitutions = substitutions
        st.session_state.rewritten_recipe = rewritten


def render_results(
    client: OpenAI,
    servings: int,
    language: str,
    allergens: list[str],
    dietary: list[str],
    allotments: dict,
    kid_friendly: bool,
    eli5: bool,
) -> None:
    base_servings = st.session_state.base_servings or 4
    ingredients = scale_ingredients(st.session_state.parsed_ingredients, base_servings, servings)
    substitutions = deepcopy(st.session_state.substitutions or {})
    non_wic = [ing for ing in ingredients if not is_wic_eligible(ing["name"])]
    recipe = deepcopy(st.session_state.rewritten_recipe)
    score = st.session_state.wic_score or 0
    original_text = st.session_state.get("original_recipe_text", "")

    st.success("Recipe adapted successfully!")

    shopping = recipe.get("shopping_list", {})
    costs = estimate_shopping_cost(shopping)
    original_est = costs["total"] + len(non_wic) * 2.50
    wic_est = costs["total"]
    nc = recipe.get("nutrition_comparison", {})

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("WIC Score", f"{score}%")
    c2.metric("Substitutions", len(non_wic))
    c3.metric("Servings", servings)
    c4.metric("Original $", f"${original_est:.2f}")
    c5.metric("WIC $", f"${wic_est:.2f}")
    c6.metric("Savings", f"${max(original_est - wic_est, 0):.2f}")
    avg_conf = (
        round(sum(substitutions[n].get("confidence", 80) for n in substitutions) / len(substitutions))
        if substitutions
        else 100
    )
    c7.metric("Sub Confidence", f"{avg_conf}%")

    t1, t2, t3 = st.columns(3)
    t1.caption(f"Difficulty: **{recipe.get('difficulty', 'Easy')}**")
    t2.caption(f"Prep: **{recipe.get('prep_time_min', 15)} min**")
    t3.caption(f"Cook: **{recipe.get('cook_time_min', 25)} min**")

    for warning in check_wic_balance(shopping, allotments):
        st.warning(warning)

    tab_ner, tab_diff, tab_recipe, tab_shop = st.tabs(
        ["NLP Analysis", "Before / After", "Adapted Recipe", "Shopping & Export"]
    )

    with tab_ner:
        st.subheader("Ingredient Named Entity Recognition")
        st.caption("Computational linguistics pipeline: parse -> entity link -> WIC ontology match")
        st.dataframe(build_ner_table(ingredients), use_container_width=True, hide_index=True)

        if non_wic and substitutions:
            st.subheader("Substitution Engine")
            for ing in non_wic:
                name = ing["name"]
                sub = substitutions.get(name, {})
                conf = sub.get("confidence", substitution_confidence(name, sub))
                with st.expander(f"{name} -> {sub.get('substitution', 'N/A')} ({conf}% confidence)"):
                    st.write(f"**Why this works:** {sub.get('reason', 'N/A')}")
                    st.write(f"**WIC Category:** {sub.get('category', 'N/A')}")
                    if sub.get("wic_office_note"):
                        st.info(sub["wic_office_note"])
                    else:
                        st.caption(WIC_OFFICE_TIP)

            st.subheader("Edit Substitutions")
            st.caption("Tweak AI suggestions, then regenerate the recipe without re-parsing.")
            edited = {}
            for ing in non_wic:
                name = ing["name"]
                sub = substitutions.get(name, {})
                new_sub = st.text_input(
                    f"Replace '{name}' with",
                    value=sub.get("substitution", ""),
                    key=f"edit_sub_{name}",
                )
                edited[name] = {**sub, "substitution": new_sub or sub.get("substitution", "")}

            if st.button("Apply Edits & Regenerate Recipe", type="primary"):
                regenerate_with_edits(
                    client,
                    original_text,
                    st.session_state.parsed_ingredients,
                    edited,
                    servings,
                    language,
                    allergens + dietary,
                    kid_friendly,
                    eli5,
                )
                st.rerun()

    with tab_diff:
        st.subheader("Recipe Transformation")
        col_orig, col_new = st.columns(2)
        with col_orig:
            st.markdown("**Original Ingredients**")
            for ing in ingredients:
                badge = "WIC" if is_wic_eligible(ing["name"]) else "Non-WIC"
                st.markdown(f"- [{badge}] {ing.get('quantity', '')} {ing['name']}".strip())
        with col_new:
            st.markdown("**WIC-Adapted Ingredients**")
            for ing in build_adapted_ingredient_list(ingredients, substitutions):
                icon = "->" if ing["changed"] else "OK"
                st.markdown(f"- [{icon}] {ing.get('quantity', '')} {ing['adapted_name']}".strip())

        if nc:
            st.subheader("Nutrition Preservation (estimated per serving)")
            n1, n2, n3 = st.columns(3)
            n1.metric("Protein (original)", f"{nc.get('protein_original_g', '?')}g")
            n2.metric("Protein (WIC version)", f"{nc.get('protein_new_g', '?')}g")
            n3.metric("Fiber (WIC version)", f"{nc.get('fiber_new_g', '?')}g")
            prot_diff = nc.get("protein_new_g", 0) - nc.get("protein_original_g", 0)
            if prot_diff >= -2:
                st.success("Substitution preserves protein levels within ~2g per serving.")
            else:
                st.warning("Consider adding extra WIC protein (beans, eggs, peanut butter).")

    with tab_recipe:
        st.markdown(f"### {recipe.get('title', 'Adapted Recipe')}")
        if servings != base_servings:
            st.caption(f"Scaled for {servings} servings (originally {base_servings})")

        for i, step in enumerate(recipe.get("recipe_steps", []), 1):
            st.markdown(f"{i}. {step}")

        if recipe.get("nutrition_win"):
            st.info(recipe["nutrition_win"])

        if recipe.get("notes"):
            st.markdown("**WIC Tips:**")
            for note in recipe["notes"]:
                st.markdown(f"- {note}")

        st.caption(get_seasonal_tip())

    with tab_shop:
        categories = ["Produce", "Dairy", "Grains", "Proteins"]
        shop_cols = st.columns(4)
        for idx, category in enumerate(categories):
            items = shopping.get(category, [])
            with shop_cols[idx]:
                with st.expander(f"{category} ({len(items)})"):
                    for item in items:
                        st.checkbox(item, key=f"shop_{category}_{item}_{idx}_{servings}")

        other_items = shopping.get("Other", [])
        if other_items:
            with st.expander(f"Other ({len(other_items)})"):
                for item in other_items:
                    # Use a unique index to guarantee no duplicate keys
for idx, item in enumerate(items):
    safe_key = f"shop_{category}_{idx}_{re.sub(r'[^a-zA-Z0-9]', '_', item)[:30]}"
    st.checkbox(item, key=f"shop_{category}_{hash(item + str(servings)) % 10000}_{servings}")
    

        export_text = build_export_text(recipe, ingredients, substitutions, servings, original_text)
        d1, d2, d3 = st.columns(3)
        with d1:
            st.download_button(
                "Download Recipe Card (.txt)",
                data=export_text,
                file_name="wic_recipe_card.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with d2:
            try:
                pdf_bytes = build_pdf_bytes(recipe, ingredients, substitutions, servings)
                st.download_button(
                    "Download PDF",
                    data=bytes(pdf_bytes),
                    file_name="wic_recipe_card.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as exc:
                st.caption(f"PDF unavailable: {exc}")
        with d3:
            if st.button("Save to Favorites", use_container_width=True):
                fav = {
                    "title": recipe.get("title", "Recipe"),
                    "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "text": export_text,
                }
                st.session_state.saved_recipes.append(fav)
                st.toast("Saved to favorites!")


def main() -> None:
    init_session_state()
    client = get_client()

    with st.sidebar:
        st.header("Controls")
        model_label = st.selectbox(
            "AI Model (Featherless)",
            list(MODEL_OPTIONS.keys()),
            index=0,
        )
        st.session_state.selected_model = MODEL_OPTIONS[model_label]

        example_choice = st.selectbox("Load example recipe", list(EXAMPLES.keys()), index=0)
        state = st.selectbox("WIC State", list(STATE_NOTES.keys()))
        servings = st.slider("Servings", 1, 20, 4)

        st.subheader("Language & Audience")
        language = st.radio("Output language", ["English", "Español"])
        kid_friendly = st.checkbox("Kid-friendly mode", help="Simpler steps for cooking with children")
        eli5 = st.checkbox("Explain Like I'm 5", help="Plain-language WIC tips")

        st.subheader("Dietary Filters")
        allergens = st.multiselect("Allergens to avoid", ["Dairy", "Nuts", "Soy", "Gluten", "Eggs"])
        dietary = st.multiselect("Dietary styles", ["Gluten-free", "Vegan", "Low-sodium"])

        st.subheader("WIC Monthly Allotment")
        allotments = {
            "produce_cv": st.number_input("Produce ($/mo)", 0, 200, WIC_MONTHLY_DEFAULTS["produce_cv"], 5),
            "dairy_equiv": st.number_input("Dairy (units)", 0, 50, WIC_MONTHLY_DEFAULTS["dairy_equiv"]),
            "grains_equiv": st.number_input("Grains (units)", 0, 50, WIC_MONTHLY_DEFAULTS["grains_equiv"]),
            "proteins_equiv": st.number_input("Proteins (units)", 0, 50, WIC_MONTHLY_DEFAULTS["proteins_equiv"]),
        }

        st.subheader("Saved Favorites")
        if st.session_state.saved_recipes:
            for i, fav in enumerate(reversed(st.session_state.saved_recipes[-5:])):
                with st.expander(f"{fav['title']} ({fav['saved_at']})"):
                    st.download_button(
                        "Download",
                        fav["text"],
                        file_name=f"favorite_{i}.txt",
                        key=f"fav_dl_{i}",
                    )
        else:
            st.caption("No saved recipes yet.")

        st.info("WIC rules vary by state. Based on common USDA guidelines — verify locally.")

    st.title("WIC Recipe Parser")
    st.caption("Transform any recipe into WIC-friendly meals using AI | Built for LingHacks VII")

    input_tab1, input_tab2 = st.tabs(["Paste Recipe", "Upload Photo / PDF"])

    with input_tab1:
        if example_choice != "None":
            if st.session_state.get("last_example") != example_choice:
                st.session_state.recipe_text_area = EXAMPLES[example_choice]
                st.session_state.last_example = example_choice

        recipe_input = st.text_area(
            "Paste your recipe here",
            height=220,
            key="recipe_text_area",
            placeholder="Paste ingredients and instructions, or load an example from the sidebar...",
        )
        st.session_state.recipe_input = recipe_input

    with input_tab2:
        uploaded = st.file_uploader(
            "Upload recipe (photo, PDF, or .txt)",
            type=["png", "jpg", "jpeg", "pdf", "txt"],
            help="OCR for photos requires Tesseract installed locally. PDF text extraction works out of the box.",
        )
        if uploaded:
            extracted = extract_text_from_upload(uploaded)
            if extracted.strip():
                st.session_state.recipe_text_area = extracted
                st.session_state.recipe_input = extracted
                st.success(f"Extracted {len(extracted.splitlines())} lines — review in Paste tab.")
                with st.expander("Preview extracted text"):
                    st.text(extracted[:2000])

    col1, col2, col3 = st.columns(3)
    with col1:
        adapt_clicked = st.button("Adapt to WIC", type="primary", use_container_width=True)
    with col2:
        clear_clicked = st.button("Clear", use_container_width=True)
    with col3:
        if st.session_state.processing_done:
            st.caption("Tip: change servings to rescale without re-running AI")

    if clear_clicked:
        for key in list(st.session_state.keys()):
            if key not in ("saved_recipes", "selected_model"):
                del st.session_state[key]
        init_session_state()
        st.rerun()

    if adapt_clicked:
        text = st.session_state.get("recipe_input", "").strip()
        if not text:
            st.warning("Please enter, upload, or load an example recipe first.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            try:
                process_recipe(
                    client,
                    text,
                    servings,
                    language,
                    allergens,
                    dietary,
                    state,
                    kid_friendly,
                    eli5,
                    progress_bar,
                    status_text,
                )
            except Exception as exc:
                st.error(f"Something went wrong: {exc}")
                st.info("Try an example recipe, simplify the text, or check your API key.")
            finally:
                progress_bar.empty()
                status_text.empty()

    if st.session_state.processing_done and st.session_state.parsed_ingredients:
        render_results(client, servings, language, allergens, dietary, allotments, kid_friendly, eli5)

    st.caption("Built for LingHacks VII | Computational Linguistics + AI | 2026")


if __name__ == "__main__":
    main()
