"""WIC Eligible Foods Database - Hardcoded for MVP"""

WIC_CATEGORIES = {
    "dairy": [
        "milk", "1% milk", "2% milk", "skim milk", "whole milk", "low-fat milk", "nonfat milk",
        "cheese", "cheddar cheese", "mozzarella cheese", "cottage cheese", "string cheese",
        "eggs", "large eggs", "yogurt", "plain yogurt", "low-fat yogurt", "nonfat yogurt",
        "lactose-free milk", "soy milk", "tofu", "swiss cheese", "american cheese",
        "part-skim mozzarella", "ricotta cheese", "cream cheese",
    ],
    "proteins": [
        "peanut butter", "almond butter", "beans", "black beans", "pinto beans", "kidney beans",
        "lentils", "canned beans", "canned tuna", "canned salmon", "sardines", "tofu",
        "eggs", "dry beans", "dry peas", "dry lentils", "chickpeas", "garbanzo beans",
        "navy beans", "great northern beans", "split peas", "refried beans", "canned chicken",
        "chunk light tuna", "pink salmon",
    ],
    "grains": [
        "brown rice", "white rice", "rice", "whole wheat bread", "whole grain bread", "bread",
        "oats", "oatmeal", "rolled oats", "steel cut oats",
        "whole wheat pasta", "pasta", "whole wheat tortillas", "tortillas", "corn tortillas",
        "quinoa", "bulgur", "barley", "whole grain cereal", "cereal", "granola",
        "whole wheat flour", "flour", "cornmeal", "whole grain crackers", "crackers",
        "whole wheat buns", "english muffins", "pita bread",
    ],
    "produce": [
        "apples", "bananas", "oranges", "grapes", "strawberries", "blueberries",
        "carrots", "broccoli", "spinach", "lettuce", "tomatoes", "potatoes", "onions",
        "peppers", "cucumber", "celery", "cabbage", "cauliflower", "green beans",
        "fresh fruit", "fresh vegetables", "frozen vegetables", "frozen fruit",
        "canned vegetables", "canned fruit", "100% juice", "orange juice", "apple juice",
        "zucchini", "squash", "sweet potatoes", "corn", "peas", "mushrooms", "garlic",
        "lemons", "limes", "avocado", "kale", "collard greens",
    ],
    "infant": [
        "infant formula", "baby formula", "infant cereal", "baby food", "baby food fruits",
        "baby food vegetables", "baby food meat", "stage 1 baby food", "stage 2 baby food",
        "stage 3 baby food", "infant oatmeal", "infant rice cereal", "baby food cereal",
        "baby food chicken", "baby food turkey", "baby food beef", "baby food squash",
        "baby food sweet potato", "baby food peas", "baby food applesauce",
        "baby food pears", "baby food bananas", "baby food carrots",
    ],
}

WIC_ALL_ITEMS: list[str] = []
for _category, _items in WIC_CATEGORIES.items():
    WIC_ALL_ITEMS.extend(_items)
WIC_ALL_ITEMS = list(set(WIC_ALL_ITEMS))


def is_wic_eligible(ingredient_name: str) -> bool:
    """Check if an ingredient is likely WIC-eligible using substring matching."""
    name = ingredient_name.lower().strip()
    for wic_item in WIC_ALL_ITEMS:
        wic_lower = wic_item.lower()
        if wic_lower in name or name in wic_lower:
            return True
    return False


def get_wic_category(ingredient_name: str) -> str:
    """Return the WIC category for an ingredient."""
    name = ingredient_name.lower().strip()
    for category, items in WIC_CATEGORIES.items():
        for wic_item in items:
            if wic_item.lower() in name or name in wic_item.lower():
                return category
    return "other"


# Typical monthly WIC cash-value produce allotment (varies by state; demo defaults)
WIC_MONTHLY_DEFAULTS = {
    "produce_cv": 47,
    "dairy_equiv": 12,
    "grains_equiv": 10,
    "proteins_equiv": 8,
}

STATE_NOTES = {
    "Federal (default)": "Uses common USDA federal WIC guidelines. Verify with your local WIC office.",
    "Texas": "TX WIC includes fresh/frozen produce CVV (~$47/mo). Some specialty items may differ.",
    "California": "CA WIC offers extensive organic produce options. Soy milk requires medical referral.",
    "Illinois": "IL WIC follows federal standards with state-specific brand restrictions on some items.",
}

SEASONAL_PRODUCE = {
    "spring": ["asparagus", "strawberries", "spinach", "peas", "lettuce"],
    "summer": ["tomatoes", "corn", "zucchini", "peaches", "watermelon", "bell pepper"],
    "fall": ["apples", "sweet potatoes", "squash", "carrots", "broccoli"],
    "winter": ["oranges", "potatoes", "cabbage", "cauliflower", "frozen vegetables"],
}

WIC_OFFICE_TIP = (
    "Contact your local WIC office to confirm eligibility for specialty items "
    "(e.g., lactose-free milk, soy milk). Rules vary by state and may require a prescription."
)


def get_current_season() -> str:
    import datetime

    month = datetime.datetime.now().month
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "fall"
    return "winter"


def get_seasonal_tip() -> str:
    season = get_current_season()
    items = ", ".join(SEASONAL_PRODUCE[season][:4])
    return f"Seasonal WIC produce ({season}): consider {items} for lower-cost substitutions."


def get_match_confidence(ingredient_name: str) -> float:
    """Return 0.0–1.0 confidence that ingredient matches a WIC database entry."""
    name = ingredient_name.lower().strip()
    if not name:
        return 0.0
    if not is_wic_eligible(name):
        return 0.0
    best = 0.0
    for wic_item in WIC_ALL_ITEMS:
        wic_lower = wic_item.lower()
        if name == wic_lower:
            return 1.0
        if wic_lower in name or name in wic_lower:
            ratio = min(len(wic_lower), len(name)) / max(len(wic_lower), len(name))
            best = max(best, ratio)
    return round(best, 2)


def substitution_confidence(ingredient_name: str, sub: dict) -> int:
    """Heuristic confidence score for a substitution suggestion (demo)."""
    if ingredient_name.lower() in FALLBACK_SUBSTITUTIONS:
        return 88
    category = sub.get("category", "other")
    if category in WIC_CATEGORIES:
        return 92
    return 75


FALLBACK_SUBSTITUTIONS: dict[str, dict[str, str]] = {
    "butter": {
        "substitution": "vegetable oil",
        "reason": "Vegetable oil is WIC-eligible and works for sautéing and baking.",
        "category": "grains",
    },
    "all-purpose flour": {
        "substitution": "whole wheat flour",
        "reason": "Whole wheat flour is WIC-eligible and adds fiber.",
        "category": "grains",
    },
    "heavy cream": {
        "substitution": "whole milk",
        "reason": "Whole milk is WIC-eligible and provides creaminess with less fat.",
        "category": "dairy",
    },
    "sour cream": {
        "substitution": "plain yogurt",
        "reason": "Plain yogurt is WIC-eligible and offers similar tang and texture.",
        "category": "dairy",
    },
    "ground beef": {
        "substitution": "canned beans",
        "reason": "Canned beans are WIC-eligible and provide protein and fiber.",
        "category": "proteins",
    },
    "chicken breast": {
        "substitution": "canned tuna or eggs",
        "reason": "Canned tuna and eggs are WIC-eligible protein sources.",
        "category": "proteins",
    },
    "olive oil": {
        "substitution": "vegetable oil",
        "reason": "Vegetable oil is WIC-eligible and suitable for cooking.",
        "category": "grains",
    },
    "soy sauce": {
        "substitution": "salt + lemon juice",
        "reason": "Salt and lemon juice add savory and bright flavor without soy.",
        "category": "produce",
    },
    "taco seasoning": {
        "substitution": "chili powder + cumin",
        "reason": "Basic spices from pantry staples mimic taco seasoning flavor.",
        "category": "produce",
    },
    "white rice": {
        "substitution": "brown rice",
        "reason": "Brown rice is WIC-eligible and higher in fiber.",
        "category": "grains",
    },
    "flour tortillas": {
        "substitution": "whole wheat tortillas",
        "reason": "Whole wheat tortillas are WIC-eligible and more nutritious.",
        "category": "grains",
    },
    "penne pasta": {
        "substitution": "whole wheat pasta",
        "reason": "Whole wheat pasta is WIC-eligible and adds whole grains.",
        "category": "grains",
    },
    "sugar": {
        "substitution": "mashed banana",
        "reason": "Mashed banana is WIC-eligible and naturally sweetens recipes.",
        "category": "produce",
    },
    "baking powder": {
        "substitution": "baking soda + yogurt",
        "reason": "Baking soda with yogurt creates leavening using WIC dairy.",
        "category": "dairy",
    },
    "vanilla extract": {
        "substitution": "cinnamon",
        "reason": "Cinnamon adds warm flavor without specialty extracts.",
        "category": "produce",
    },
    "mayonnaise": {
        "substitution": "plain yogurt",
        "reason": "Plain yogurt is WIC-eligible and works in dressings and spreads.",
        "category": "dairy",
    },
    "bread crumbs": {
        "substitution": "oats",
        "reason": "Oats are WIC-eligible and make a great crunchy coating.",
        "category": "grains",
    },
    "parmesan cheese": {
        "substitution": "cheddar cheese",
        "reason": "Cheddar cheese is WIC-eligible and melts well in pasta dishes.",
        "category": "dairy",
    },
    "cream cheese": {
        "substitution": "cottage cheese blended smooth",
        "reason": "Cottage cheese is WIC-eligible and can be blended for spreadable texture.",
        "category": "dairy",
    },
    "half and half": {
        "substitution": "whole milk",
        "reason": "Whole milk is WIC-eligible and works in most creamy recipes.",
        "category": "dairy",
    },
    "whipping cream": {
        "substitution": "whole milk",
        "reason": "Whole milk is WIC-eligible; chill well for lighter whipped texture.",
        "category": "dairy",
    },
    "ground turkey": {
        "substitution": "canned beans or eggs",
        "reason": "Beans and eggs are WIC-eligible lean protein alternatives.",
        "category": "proteins",
    },
    "ground pork": {
        "substitution": "canned beans",
        "reason": "Canned beans provide WIC-eligible protein and fiber.",
        "category": "proteins",
    },
    "bacon": {
        "substitution": "canned tuna",
        "reason": "Canned tuna adds savory umami as a WIC-eligible protein.",
        "category": "proteins",
    },
    "sausage": {
        "substitution": "peanut butter",
        "reason": "Peanut butter is WIC-eligible and adds rich savory flavor.",
        "category": "proteins",
    },
    "shrimp": {
        "substitution": "canned tuna",
        "reason": "Canned tuna is WIC-eligible seafood with similar protein content.",
        "category": "proteins",
    },
    "salmon fillet": {
        "substitution": "canned salmon",
        "reason": "Canned salmon is WIC-eligible and rich in omega-3s.",
        "category": "proteins",
    },
    "sesame oil": {
        "substitution": "vegetable oil",
        "reason": "Vegetable oil is WIC-eligible for stir-frying and sautéing.",
        "category": "grains",
    },
    "coconut oil": {
        "substitution": "vegetable oil",
        "reason": "Vegetable oil is WIC-eligible and neutral for baking.",
        "category": "grains",
    },
    "canola oil": {
        "substitution": "vegetable oil",
        "reason": "Vegetable oil is WIC-eligible and interchangeable in recipes.",
        "category": "grains",
    },
    "white bread": {
        "substitution": "whole wheat bread",
        "reason": "Whole wheat bread is WIC-eligible and higher in fiber.",
        "category": "grains",
    },
    "white flour": {
        "substitution": "whole wheat flour",
        "reason": "Whole wheat flour is WIC-eligible whole grain option.",
        "category": "grains",
    },
    "spaghetti": {
        "substitution": "whole wheat pasta",
        "reason": "Whole wheat pasta is WIC-eligible and nutritionally superior.",
        "category": "grains",
    },
    "egg noodles": {
        "substitution": "whole wheat pasta",
        "reason": "Whole wheat pasta is WIC-eligible and holds sauce well.",
        "category": "grains",
    },
    "corn starch": {
        "substitution": "whole wheat flour",
        "reason": "Whole wheat flour can thicken sauces as a WIC-eligible option.",
        "category": "grains",
    },
    "honey": {
        "substitution": "mashed banana",
        "reason": "Mashed banana is WIC-eligible natural sweetener.",
        "category": "produce",
    },
    "maple syrup": {
        "substitution": "mashed banana",
        "reason": "Mashed banana adds sweetness using WIC-eligible produce.",
        "category": "produce",
    },
    "brown sugar": {
        "substitution": "mashed banana",
        "reason": "Mashed banana sweetens recipes with WIC-eligible fruit.",
        "category": "produce",
    },
    "powdered sugar": {
        "substitution": "mashed banana",
        "reason": "Mashed banana provides natural sweetness for WIC-friendly baking.",
        "category": "produce",
    },
    "worcestershire sauce": {
        "substitution": "salt + lemon juice",
        "reason": "Salt and lemon juice add savory depth without specialty sauces.",
        "category": "produce",
    },
    "fish sauce": {
        "substitution": "salt + lemon juice",
        "reason": "Salt and lemon juice mimic umami and brightness.",
        "category": "produce",
    },
    "balsamic vinegar": {
        "substitution": "lemon juice",
        "reason": "Lemon juice is WIC-eligible and adds acidity to dishes.",
        "category": "produce",
    },
    "red wine vinegar": {
        "substitution": "lemon juice",
        "reason": "Lemon juice provides WIC-eligible acidity.",
        "category": "produce",
    },
    "apple cider vinegar": {
        "substitution": "lemon juice",
        "reason": "Lemon juice is WIC-eligible and adds tang.",
        "category": "produce",
    },
    "mirin": {
        "substitution": "orange juice",
        "reason": "100% orange juice is WIC-eligible and adds subtle sweetness.",
        "category": "produce",
    },
    "rice vinegar": {
        "substitution": "lemon juice",
        "reason": "Lemon juice is WIC-eligible for brightening flavors.",
        "category": "produce",
    },
    "beef broth": {
        "substitution": "canned vegetables + water",
        "reason": "Vegetable broth from WIC canned veggies adds flavor.",
        "category": "produce",
    },
    "chicken broth": {
        "substitution": "canned vegetables + water",
        "reason": "Simmered canned vegetables make a WIC-eligible broth base.",
        "category": "produce",
    },
    "vegetable broth": {
        "substitution": "canned vegetables + water",
        "reason": "Canned vegetables are WIC-eligible for homemade broth.",
        "category": "produce",
    },
    "cream of mushroom soup": {
        "substitution": "whole milk + mushrooms",
        "reason": "Whole milk and fresh mushrooms create a WIC-eligible creamy base.",
        "category": "dairy",
    },
    "tomato paste": {
        "substitution": "canned tomatoes",
        "reason": "Canned tomatoes are WIC-eligible and can be reduced for paste.",
        "category": "produce",
    },
    "sun-dried tomatoes": {
        "substitution": "fresh tomatoes",
        "reason": "Fresh tomatoes are WIC-eligible produce.",
        "category": "produce",
    },
    "artichoke hearts": {
        "substitution": "canned vegetables",
        "reason": "Canned vegetables are WIC-eligible alternatives.",
        "category": "produce",
    },
    "kalamata olives": {
        "substitution": "canned vegetables",
        "reason": "Canned vegetables provide WIC-eligible savory additions.",
        "category": "produce",
    },
    "prosciutto": {
        "substitution": "canned tuna",
        "reason": "Canned tuna adds savory saltiness as WIC-eligible protein.",
        "category": "proteins",
    },
    "pancetta": {
        "substitution": "peanut butter",
        "reason": "Peanut butter adds rich flavor as a WIC-eligible protein.",
        "category": "proteins",
    },
    "nutella": {
        "substitution": "peanut butter + mashed banana",
        "reason": "Peanut butter and banana are both WIC-eligible.",
        "category": "proteins",
    },
    "almond milk": {
        "substitution": "soy milk",
        "reason": "Soy milk is WIC-eligible dairy alternative.",
        "category": "dairy",
    },
    "coconut milk": {
        "substitution": "whole milk",
        "reason": "Whole milk is WIC-eligible and creamy for curries and soups.",
        "category": "dairy",
    },
    "evaporated milk": {
        "substitution": "whole milk",
        "reason": "Whole milk is WIC-eligible; simmer to reduce for similar richness.",
        "category": "dairy",
    },
    "condensed milk": {
        "substitution": "whole milk + mashed banana",
        "reason": "Whole milk and banana sweeten recipes with WIC items.",
        "category": "dairy",
    },
    "buttermilk": {
        "substitution": "plain yogurt thinned with milk",
        "reason": "Yogurt and milk are WIC-eligible buttermilk substitutes.",
        "category": "dairy",
    },
    "mascarpone": {
        "substitution": "cottage cheese blended with yogurt",
        "reason": "Cottage cheese and yogurt are WIC-eligible creamy substitutes.",
        "category": "dairy",
    },
    "ricotta": {
        "substitution": "cottage cheese",
        "reason": "Cottage cheese is WIC-eligible with similar texture.",
        "category": "dairy",
    },
    "feta cheese": {
        "substitution": "cottage cheese",
        "reason": "Cottage cheese is WIC-eligible and crumbles similarly.",
        "category": "dairy",
    },
    "goat cheese": {
        "substitution": "cheddar cheese",
        "reason": "Cheddar cheese is WIC-eligible and melts well.",
        "category": "dairy",
    },
    "blue cheese": {
        "substitution": "cheddar cheese",
        "reason": "Cheddar cheese is WIC-eligible for salads and dressings.",
        "category": "dairy",
    },
    "mozzarella": {
        "substitution": "part-skim mozzarella",
        "reason": "Part-skim mozzarella is WIC-eligible.",
        "category": "dairy",
    },
    "provolone": {
        "substitution": "cheddar cheese",
        "reason": "Cheddar cheese is WIC-eligible melting cheese.",
        "category": "dairy",
    },
    "swiss cheese": {
        "substitution": "cheddar cheese",
        "reason": "Cheddar cheese is WIC-eligible sandwich cheese.",
        "category": "dairy",
    },
    "pesto": {
        "substitution": "peanut butter + spinach",
        "reason": "Peanut butter and spinach are WIC-eligible pesto base.",
        "category": "proteins",
    },
    "hoisin sauce": {
        "substitution": "peanut butter + orange juice",
        "reason": "Peanut butter and orange juice create a WIC-eligible glaze.",
        "category": "proteins",
    },
    "teriyaki sauce": {
        "substitution": "orange juice + soy-free seasoning",
        "reason": "Orange juice adds sweetness; salt and spices add savory notes.",
        "category": "produce",
    },
    "sriracha": {
        "substitution": "chili powder + lemon juice",
        "reason": "Pantry spices add heat without specialty hot sauce.",
        "category": "produce",
    },
    "hot sauce": {
        "substitution": "chili powder + lemon juice",
        "reason": "Basic spices provide heat as a WIC-friendly alternative.",
        "category": "produce",
    },
    "dijon mustard": {
        "substitution": "salt + lemon juice",
        "reason": "Salt and lemon juice add tang without specialty condiments.",
        "category": "produce",
    },
    "ketchup": {
        "substitution": "canned tomatoes + mashed banana",
        "reason": "Canned tomatoes and banana make a WIC-eligible sweet sauce.",
        "category": "produce",
    },
    "bbq sauce": {
        "substitution": "canned tomatoes + mashed banana",
        "reason": "Tomatoes and banana create a WIC-eligible sweet-savory sauce.",
        "category": "produce",
    },
    "ranch dressing": {
        "substitution": "plain yogurt + dried herbs",
        "reason": "Plain yogurt is WIC-eligible creamy dressing base.",
        "category": "dairy",
    },
    "italian dressing": {
        "substitution": "vegetable oil + lemon juice",
        "reason": "Oil and lemon juice make a simple WIC-eligible vinaigrette.",
        "category": "grains",
    },
    "caesar dressing": {
        "substitution": "plain yogurt + lemon juice",
        "reason": "Yogurt and lemon create a WIC-eligible creamy dressing.",
        "category": "dairy",
    },
    "panko breadcrumbs": {
        "substitution": "oats",
        "reason": "Oats are WIC-eligible and make excellent crispy coating.",
        "category": "grains",
    },
    "self-rising flour": {
        "substitution": "whole wheat flour + baking soda + yogurt",
        "reason": "Whole wheat flour with leavening agents is WIC-eligible.",
        "category": "grains",
    },
    "cake flour": {
        "substitution": "whole wheat flour",
        "reason": "Whole wheat flour is WIC-eligible for baking.",
        "category": "grains",
    },
    "instant ramen": {
        "substitution": "whole wheat pasta",
        "reason": "Whole wheat pasta is WIC-eligible noodle substitute.",
        "category": "grains",
    },
    "udon noodles": {
        "substitution": "whole wheat pasta",
        "reason": "Whole wheat pasta works in stir-fries and soups.",
        "category": "grains",
    },
    "rice noodles": {
        "substitution": "brown rice",
        "reason": "Brown rice is WIC-eligible grain base for the dish.",
        "category": "grains",
    },
    "couscous": {
        "substitution": "bulgur",
        "reason": "Bulgur is WIC-eligible whole grain with similar texture.",
        "category": "grains",
    },
    "quinoa": {
        "substitution": "brown rice",
        "reason": "Brown rice is WIC-eligible whole grain.",
        "category": "grains",
    },
    "polenta": {
        "substitution": "cornmeal",
        "reason": "Cornmeal is WIC-eligible and makes similar dishes.",
        "category": "grains",
    },
    "tortilla chips": {
        "substitution": "corn tortillas baked crisp",
        "reason": "Corn tortillas are WIC-eligible; bake for crunchy chips.",
        "category": "grains",
    },
    "pita chips": {
        "substitution": "whole wheat bread toasted",
        "reason": "Whole wheat bread is WIC-eligible when toasted crisp.",
        "category": "grains",
    },
    "granola bars": {
        "substitution": "oats + peanut butter",
        "reason": "Oats and peanut butter are WIC-eligible snack ingredients.",
        "category": "grains",
    },
    "protein powder": {
        "substitution": "peanut butter",
        "reason": "Peanut butter is WIC-eligible protein boost.",
        "category": "proteins",
    },
    "tofu": {
        "substitution": "canned beans",
        "reason": "Canned beans are WIC-eligible plant protein.",
        "category": "proteins",
    },
    "tempeh": {
        "substitution": "canned beans",
        "reason": "Canned beans provide WIC-eligible plant protein.",
        "category": "proteins",
    },
    "edamame": {
        "substitution": "green beans",
        "reason": "Green beans are WIC-eligible vegetable protein side.",
        "category": "produce",
    },
    "snap peas": {
        "substitution": "green beans",
        "reason": "Green beans are WIC-eligible crunchy vegetable.",
        "category": "produce",
    },
    "asparagus": {
        "substitution": "broccoli",
        "reason": "Broccoli is WIC-eligible green vegetable.",
        "category": "produce",
    },
    "eggplant": {
        "substitution": "zucchini",
        "reason": "Zucchini is WIC-eligible and absorbs flavors similarly.",
        "category": "produce",
    },
    "arugula": {
        "substitution": "spinach",
        "reason": "Spinach is WIC-eligible leafy green.",
        "category": "produce",
    },
    "mixed greens": {
        "substitution": "lettuce",
        "reason": "Lettuce is WIC-eligible salad base.",
        "category": "produce",
    },
    "fresh herbs": {
        "substitution": "dried herbs from pantry",
        "reason": "Dried herbs add flavor without specialty fresh produce.",
        "category": "produce",
    },
    "basil": {
        "substitution": "spinach",
        "reason": "Spinach adds green color and mild flavor as WIC produce.",
        "category": "produce",
    },
    "cilantro": {
        "substitution": "lettuce",
        "reason": "Lettuce adds fresh crunch as WIC-eligible garnish.",
        "category": "produce",
    },
    "parsley": {
        "substitution": "spinach",
        "reason": "Spinach is WIC-eligible green garnish.",
        "category": "produce",
    },
    "ginger": {
        "substitution": "lemon juice",
        "reason": "Lemon juice adds brightness as WIC-eligible flavor booster.",
        "category": "produce",
    },
    "wine": {
        "substitution": "orange juice",
        "reason": "100% orange juice is WIC-eligible cooking liquid.",
        "category": "produce",
    },
    "beer": {
        "substitution": "orange juice",
        "reason": "Orange juice adds moisture and subtle sweetness.",
        "category": "produce",
    },
    "stock cubes": {
        "substitution": "canned vegetables + water",
        "reason": "Simmered canned vegetables make WIC-eligible broth.",
        "category": "produce",
    },
    "gelatin": {
        "substitution": "mashed banana",
        "reason": "Mashed banana helps bind and sweeten WIC-friendly desserts.",
        "category": "produce",
    },
    "chocolate chips": {
        "substitution": "mashed banana + peanut butter",
        "reason": "Banana and peanut butter are WIC-eligible sweet additions.",
        "category": "produce",
    },
    "cocoa powder": {
        "substitution": "peanut butter",
        "reason": "Peanut butter adds rich flavor in WIC-friendly baking.",
        "category": "proteins",
    },
    "cream of tartar": {
        "substitution": "lemon juice",
        "reason": "Lemon juice provides acidity for egg white stabilization.",
        "category": "produce",
    },
    "shortening": {
        "substitution": "vegetable oil",
        "reason": "Vegetable oil is WIC-eligible fat for baking.",
        "category": "grains",
    },
    "lard": {
        "substitution": "vegetable oil",
        "reason": "Vegetable oil is WIC-eligible cooking fat.",
        "category": "grains",
    },
    "duck fat": {
        "substitution": "vegetable oil",
        "reason": "Vegetable oil is WIC-eligible for roasting and frying.",
        "category": "grains",
    },
    "truffle oil": {
        "substitution": "vegetable oil",
        "reason": "Vegetable oil is WIC-eligible neutral cooking oil.",
        "category": "grains",
    },
    "anchovies": {
        "substitution": "canned tuna",
        "reason": "Canned tuna adds savory depth as WIC-eligible protein.",
        "category": "proteins",
    },
    "clam juice": {
        "substitution": "canned vegetables + water",
        "reason": "Vegetable broth from WIC canned veggies adds base flavor.",
        "category": "produce",
    },
    "oyster sauce": {
        "substitution": "salt + mashed banana",
        "reason": "Salt and banana mimic sweet-savory glaze flavors.",
        "category": "produce",
    },
    "miso paste": {
        "substitution": "peanut butter + salt",
        "reason": "Peanut butter adds umami richness as WIC protein.",
        "category": "proteins",
    },
    "curry paste": {
        "substitution": "chili powder + cumin",
        "reason": "Basic spices create WIC-friendly curry flavor.",
        "category": "produce",
    },
    "garam masala": {
        "substitution": "cumin + cinnamon",
        "reason": "Pantry spices approximate warm Indian seasoning.",
        "category": "produce",
    },
    "italian seasoning": {
        "substitution": "dried oregano substitute with dried herbs",
        "reason": "Basic dried herbs add Mediterranean flavor.",
        "category": "produce",
    },
    "poultry seasoning": {
        "substitution": "salt + pepper",
        "reason": "Simple seasoning works with WIC protein sources.",
        "category": "produce",
    },
    "old bay seasoning": {
        "substitution": "salt + chili powder",
        "reason": "Salt and chili powder add savory spice.",
        "category": "produce",
    },
    "cajun seasoning": {
        "substitution": "chili powder + cumin",
        "reason": "Pantry spices create bold WIC-friendly seasoning.",
        "category": "produce",
    },
    "everything bagel seasoning": {
        "substitution": "oats + salt",
        "reason": "Oats and salt add texture and flavor as WIC items.",
        "category": "grains",
    },
    "nut butter": {
        "substitution": "peanut butter",
        "reason": "Peanut butter is WIC-eligible nut butter.",
        "category": "proteins",
    },
    "almonds": {
        "substitution": "peanut butter",
        "reason": "Peanut butter is WIC-eligible nut alternative.",
        "category": "proteins",
    },
    "walnuts": {
        "substitution": "peanut butter",
        "reason": "Peanut butter provides WIC-eligible crunch and fat.",
        "category": "proteins",
    },
    "pecans": {
        "substitution": "peanut butter",
        "reason": "Peanut butter is WIC-eligible nut substitute.",
        "category": "proteins",
    },
    "cashews": {
        "substitution": "peanut butter",
        "reason": "Peanut butter is WIC-eligible creamy nut alternative.",
        "category": "proteins",
    },
    "pine nuts": {
        "substitution": "peanut butter",
        "reason": "Peanut butter adds nutty flavor as WIC protein.",
        "category": "proteins",
    },
    "sunflower seeds": {
        "substitution": "peanut butter",
        "reason": "Peanut butter is WIC-eligible seed/nut alternative.",
        "category": "proteins",
    },
    "chia seeds": {
        "substitution": "oats",
        "reason": "Oats are WIC-eligible binding and fiber ingredient.",
        "category": "grains",
    },
    "flax seeds": {
        "substitution": "oats",
        "reason": "Oats provide WIC-eligible fiber in baking.",
        "category": "grains",
    },
    "hemp seeds": {
        "substitution": "peanut butter",
        "reason": "Peanut butter is WIC-eligible protein topping.",
        "category": "proteins",
    },
    "poppy seeds": {
        "substitution": "oats",
        "reason": "Oats add texture as WIC-eligible topping.",
        "category": "grains",
    },
    "sesame seeds": {
        "substitution": "peanut butter",
        "reason": "Peanut butter adds nutty flavor as WIC protein.",
        "category": "proteins",
    },
}
