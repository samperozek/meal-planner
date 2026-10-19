"""Check a recipe collection against config.json before planning with it.

  python3 setup/tools/validate_recipes.py          # report, exit 1 if there are errors

ERRORS (must fix): unreadable files, missing fields, duplicate ids, allergens, videos without URLs.
WARNINGS (review): thin pools, ingredient lines without quantities, weeknight hands-on over the cap,
recipes without a source, disliked ingredients, equipment the cook doesn't have.
"""
import os, re, sys
from collections import Counter, defaultdict

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KIT, "planner"))
import config  # noqa: E402  (exits with a clear message if config.json is missing)
import recipes  # noqa: E402
from pantry import QTY  # noqa: E402

ALLERGEN_WORDS = {
    "peanut": ["peanut"],
    "tree nut": ["almond", "cashew", "walnut", "pecan", "pistachio", "hazelnut", "macadamia", "pine nut"],
    "shellfish": ["shrimp", "prawn", "crab", "lobster", "scallop", "clam", "mussel", "oyster", "crawfish"],
    "fish": ["salmon", "cod", "tuna", "halibut", "tilapia", "anchov", "fish sauce", "trout", "sardine", "branzino"],
    "dairy": ["milk", "cheese", "butter", "cream", "yogurt", "ghee", "parmesan", "mozzarella", "feta", "ricotta"],
    "egg": ["egg"],
    "gluten": ["flour", "bread", "pasta", "noodle", "wheat", "barley", "panko", "tortilla", "couscous", "farro"],
    "wheat": ["flour", "bread", "pasta", "wheat", "panko", "couscous"],
    "soy": ["soy", "tofu", "edamame", "miso", "tempeh"],
    "sesame": ["sesame", "tahini"],
}
EQUIPMENT_WORDS = {"slow cooker": ["slow cooker", "crockpot", "crock-pot"], "instant pot": ["instant pot", "pressure cook"],
                   "grill": ["grill"], "smoker": ["smoker", "pellet grill"], "air fryer": ["air fryer", "air-fry"],
                   "stand mixer": ["stand mixer"]}
NO_QTY_OK = re.compile(r"to taste|for serving|serving|optional|garnish|as needed|for the pan|for frying|pinch|"
                       r"for drizzling|drizzle|to serve|handful|juice of|zest of|a few|splash", re.I)
OPTIONAL_GROUP = re.compile(r"\s*(optional|alternative|variation|substitute)", re.I)


def words_for(term):
    t = term.lower().strip()
    return ALLERGEN_WORDS.get(t) or ALLERGEN_WORDS.get(t.rstrip("s")) or [t]


def minutes(s):
    m = re.search(r"(\d+)\s*(hr|hour)", s or "")
    mins = int(m.group(1)) * 60 if m else 0
    m2 = re.search(r"(\d+)\s*min", s or "")
    return mins + (int(m2.group(1)) if m2 else 0) if (m or m2) else None


def main():
    errors, warns = [], []
    try:
        recs = recipes.load()
    except SystemExit as e:
        print("ERROR", e); sys.exit(1)
    C = config.C
    diet = C.get("diet", {})
    cooking = C.get("cooking", {})
    cap = cooking.get("weeknight_hands_on_max", 20)
    have = {e.lower() for e in cooking.get("equipment", [])}
    by_folder = defaultdict(list)
    for r in recs:
        by_folder[r["folder"]].append(r)

    # pools
    dinner_total = 0
    for slot, folders in config.POOLS.items():
        for f in folders:
            n = len(by_folder.get(f, []))
            dinner_total += n
            if n == 0:
                warns.append(f"Pool '{slot}' lists folder '{f}', which has no recipes yet")
    need = 4 * cooking.get("max_cook_nights", 5)
    if dinner_total < need:
        warns.append(f"Only {dinner_total} dinners across the pools; aim for at least {need} so dishes don't repeat too often")
    for label, pool in (("breakfast", config.BREAKFAST), ("lunch", config.LUNCH)):
        n = sum(1 for r in recs if r["folder"] == pool["folder"] and r["section"] == pool["section"])
        if n < 2:
            warns.append(f"The {label} pool ({pool['folder']} › {pool['section']}) has {n} recipe(s); 6–10 rotate best")
    if config.LESSON_FOLDER:
        lessons = by_folder.get(config.LESSON_FOLDER, [])
        if not lessons:
            warns.append(f"Lesson folder '{config.LESSON_FOLDER}' has no lessons yet")
        for r in lessons:
            if not re.search(r"\d", r["id"]):
                errors.append(f"{r['id']}: lesson ids need numbers for ordering (e.g. CS-1.1)")

    titles = Counter(r["title"].lower() for r in recs)
    core_folders = set(config.POOLS.get("core", []))
    for r in recs:
        rid = r["id"]
        lines = [l for _, items in r["ingredients"] for l in items]
        text = " ".join(lines + [t for st in r["steps"] for t in st]).lower()
        for a in diet.get("allergies", []):
            for w in words_for(a):
                hit = next((l for l in lines if w in l.lower() and "free" not in l.lower()), None)
                if hit:
                    errors.append(f"{rid}: contains '{w}' (allergy: {a}) → \"{hit[:70]}\"")
                    break
        for a in diet.get("avoid", []):
            stems = [re.sub(r"(es|s)$", "", w.lower()) for w in words_for(a)]
            if any(re.search(r"\b" + re.escape(st) + r"(e?s)?\b", text) for st in stems):
                warns.append(f"{rid}: mentions '{a}', which the cook avoids")
        req = [l for g, items in r["ingredients"] if not OPTIONAL_GROUP.match(g or "") for l in items]
        noqty = [l for l in req if not QTY.match(l.lower()) and not NO_QTY_OK.search(l)]
        if noqty:
            warns.append(f"{rid}: {len(noqty)} ingredient line(s) without a quantity, e.g. \"{noqty[0][:60]}\"")
        p = minutes(r.get("hands_on") or r.get("prep"))
        if r["folder"] in core_folders and p and p > cap:
            warns.append(f"{rid}: hands-on {r.get('hands_on') or r.get('prep')} is over the {cap}-minute weeknight cap")
        if isinstance(r.get("rating"), str) and "/" in r["rating"]:
            errors.append(f"{rid}: 'rating' is for the cook's own score; put the published rating in 'source'")
        if not r.get("url") and not r.get("source"):
            warns.append(f"{rid}: no source or URL cited (collections should be established, published recipes)")
        for v in r.get("videos") or []:
            if not v.get("url"):
                errors.append(f"{rid}: a video has no URL")
        for eq, ws in EQUIPMENT_WORDS.items():
            if any(w in text for w in ws) and have and eq not in have:
                warns.append(f"{rid}: seems to need a {eq}, which isn't in cooking.equipment")
        if titles[r["title"].lower()] > 1:
            warns.append(f"{rid}: another recipe has the same title")

    print(f"{len(recs)} recipes in {len(by_folder)} folders: " + ", ".join(f"{f} {len(v)}" for f, v in sorted(by_folder.items())))
    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"\n{len(errors)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
