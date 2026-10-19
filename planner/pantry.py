"""Pantry tracker: estimated levels of shelf-stable staples, drawn down by the recipes you cook.

pantry.json is the source of truth (pantry.txt is a generated, readable copy; the "Pantry" tab of Cook_Log.xlsx too).
Stock is added ONLY from confirmed orders (order-confirmation emails), never when a cart is filled.
Staples assumed on hand but never seen in a confirmed order are "untracked": they are skipped on grocery lists,
not drawn down and not reordered, until a confirmed order includes them.
Levels are estimates: recipe quantities are parsed from the published ingredient lines and converted to a base unit
(tsp for spices, liquids and pastes; g for dry goods; each for counted items).

  pantry.py status                  print every item with its estimated level
  pantry.py skip-list               names the grocery list should skip (on hand, not low)
  pantry.py usage PLAN.json         what that plan's meals will use from the pantry
  pantry.py check PLAN.json         items that will run low by the end of that plan → buy (prints LOW lines)
  pantry.py restock KEY [KEY ...] --order ID   a CONFIRMED order (from the order-confirmation email) included a package of each
  pantry.py order-seen ID           SEEN / NEW: has this confirmed order already been applied?
  pantry.py match "ingredient or product name"   the pantry key it belongs to (or NONE)
  pantry.py reset                   start fresh: forget all levels, deductions and applied orders (tracking starts today)
  pantry.py since                   the tracking start date as YYYY/MM/DD (orders before it are never applied)
  pantry.py unstock KEY [KEY ...]   undo a restock whose item was dropped from a cart
  pantry.py deduct [DATE]           subtract planned meals before DATE (default today) that weren't logged as skipped
  pantry.py set KEY LEVEL           a correction: full | half | low | empty | a number in the item's unit
"""
import datetime as dt, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = config.DATA
PANTRY = os.path.join(config.STATE, "pantry.json")
PANTRY_TXT = os.path.join(config.DATA, "pantry.txt")

TSP = {"tsp": 1, "teaspoon": 1, "teaspoons": 1, "tbsp": 3, "tablespoon": 3, "tablespoons": 3, "cup": 48, "cups": 48,
       "ml": 1 / 4.93, "l": 1000 / 4.93, "fl oz": 6, "oz": 6}
G_PER_CUP = {"flour": 125, "sugar": 200, "brown_sugar": 213, "white_rice": 185, "brown_rice": 190, "quinoa": 170,
             "lentils": 192, "cornstarch": 128}

# key: (name, unit, package description, package size in unit, reorder below, match regex, exclude regex)
# Ordered: the first matching item claims an ingredient line, so specific items come before general ones.
DEFAULTS = [
    ("red_pepper_flakes", "Red pepper flakes", "tsp", "1.5 oz jar", 20, 4, r"red pepper flakes|crushed red pepper|chili flakes", None),
    ("cayenne", "Cayenne pepper", "tsp", "2 oz jar", 25, 3, r"cayenne", None),
    ("smoked_paprika", "Smoked paprika", "tsp", "2 oz jar", 25, 4, r"smoked paprika", None),
    ("sweet_paprika", "Sweet paprika", "tsp", "3 oz jar", 36, 6, r"paprika", None),
    ("chili_powder", "Chili powder", "tsp", "2.5 oz jar", 30, 6, r"chili powder", None),
    ("curry_powder", "Curry powder", "tsp", "3 oz jar", 34, 6, r"curry powder", None),
    ("garam_masala", "Garam masala", "tsp", "2 oz jar", 24, 4, r"garam masala", None),
    ("cumin", "Ground cumin", "tsp", "2 oz jar", 24, 4, r"cumin", None),
    ("coriander", "Ground coriander", "tsp", "1.5 oz jar", 18, 3, r"ground coriander|coriander powder", None),
    ("turmeric", "Ground turmeric", "tsp", "2 oz jar", 24, 3, r"turmeric", None),
    ("cinnamon", "Ground cinnamon", "tsp", "2 oz jar", 24, 3, r"cinnamon", r"stick"),
    ("garlic_powder", "Garlic powder", "tsp", "3 oz jar", 30, 4, r"garlic powder", None),
    ("onion_powder", "Onion powder", "tsp", "2.5 oz jar", 28, 4, r"onion powder", None),
    ("italian_seasoning", "Italian seasoning", "tsp", "0.75 oz jar", 20, 3, r"italian seasoning", None),
    ("oregano", "Dried oregano", "tsp", "0.75 oz jar", 20, 3, r"dried oregano|oregano", r"fresh oregano"),
    ("thyme", "Dried thyme", "tsp", "0.75 oz jar", 20, 3, r"dried thyme", None),
    ("bay_leaves", "Bay leaves", "each", "0.15 oz jar", 20, 4, r"bay lea", None),
    ("black_pepper", "Black pepper", "tsp", "4 oz grinder refill", 40, 6, r"black pepper|ground pepper|peppercorn|pepper, to taste|and pepper", r"bell|cayenne|flakes|chili|jalape|red pepper"),
    ("kosher_salt", "Kosher salt", "tsp", "3 lb box", 480, 40, r"kosher salt|cooking/kosher", None),
    ("sea_salt", "Fine sea salt", "tsp", "26 oz canister", 120, 15, r"\bsalt\b", r"unsalted|salted butter"),
    ("evoo", "Extra-virgin olive oil", "tsp", "1 L bottle", 203, 30, r"olive oil", None),
    ("sesame_oil", "Toasted sesame oil", "tsp", "8.4 oz bottle", 50, 6, r"sesame oil", None),
    ("coconut_oil", "Coconut oil", "tsp", "14 oz jar", 84, 6, r"coconut oil", None),
    ("neutral_oil", "Neutral oil (avocado/canola)", "tsp", "33.8 oz bottle", 203, 30, r"vegetable oil|canola oil|avocado oil|neutral oil|cooking oil|\boil\b", r"olive|sesame|coconut|chili oil"),
    ("cooking_spray", "Nonstick cooking spray", "each", "1 can", 1, 0, r"cooking spray|nonstick spray", None),
    ("red_wine_vinegar", "Red wine vinegar", "tsp", "16 oz bottle", 96, 8, r"red wine vinegar", None),
    ("white_wine_vinegar", "White wine vinegar", "tsp", "16 oz bottle", 96, 8, r"white wine vinegar", None),
    ("cider_vinegar", "Apple cider vinegar", "tsp", "16 oz bottle", 96, 8, r"cider vinegar", None),
    ("rice_vinegar", "Rice vinegar", "tsp", "12 oz bottle", 72, 6, r"rice vinegar|rice wine vinegar", None),
    ("soy_sauce", "Soy sauce", "tsp", "15 oz bottle", 90, 9, r"soy sauce|tamari", None),
    ("dijon", "Dijon mustard", "tsp", "8 oz jar", 45, 6, r"dijon", None),
    ("ketchup", "Ketchup", "tsp", "20 oz bottle", 100, 9, r"ketchup", None),
    ("mayo", "Mayonnaise", "tsp", "30 oz jar", 170, 12, r"mayonnaise|\bmayo\b", None),
    ("hot_sauce", "Hot sauce", "tsp", "5 oz bottle", 30, 3, r"hot sauce", None),
    ("honey", "Honey", "tsp", "12 oz bottle", 48, 9, r"\bhoney\b", None),
    ("maple_syrup", "Maple syrup", "tsp", "12 oz bottle", 72, 9, r"maple syrup", None),
    ("vanilla", "Vanilla extract", "tsp", "2 oz bottle", 12, 3, r"vanilla", None),
    ("tomato_paste", "Tomato paste (tube)", "tsp", "6.5 oz tube", 33, 6, r"tomato paste", None),
    ("chicken_broth", "Chicken broth (boxed)", "tsp", "32 oz box", 192, 48, r"chicken broth|chicken stock|\bbroth\b|\bstock\b", r"vegetable"),
    ("sesame_seeds", "Toasted sesame seeds", "tsp", "1.9 oz jar", 18, 3, r"sesame seeds", None),
    ("flour", "All-purpose flour", "g", "5 lb bag", 2268, 300, r"all-purpose flour|\bflour\b", r"almond|rice flour|tortilla"),
    ("sugar", "Granulated sugar", "g", "4 lb bag", 1814, 200, r"granulated sugar|\bsugar\b", r"brown|coconut|powdered|free"),
    ("brown_sugar", "Light brown sugar", "g", "2 lb bag", 907, 150, r"brown sugar|coconut sugar", None),
    ("cornstarch", "Cornstarch", "g", "16 oz box", 454, 60, r"cornstarch|corn starch", None),
    ("baking_powder", "Baking powder", "tsp", "10 oz can", 56, 4, r"baking powder", None),
    ("baking_soda", "Baking soda", "tsp", "1 lb box", 90, 4, r"baking soda", None),
    ("white_rice", "Long-grain white rice", "g", "2 lb bag", 907, 200, r"white rice|jasmine rice|basmati rice|long-grain rice", None),
    ("brown_rice", "Brown rice", "g", "2 lb bag", 907, 200, r"brown rice", None),
    ("quinoa", "Quinoa", "g", "16 oz bag", 454, 100, r"quinoa", None),
    ("lentils", "Green/brown lentils", "g", "16 oz bag", 454, 100, r"lentils", r"red lentil|\bdal\b|toor|masoor|moong|urad|chana dal|split"),
    ("butter", "Unsalted butter", "tsp", "1 lb (4 sticks)", 96, 18, r"\bbutter\b", r"peanut butter|almond butter|buttermilk|apple butter"),
]
FIELDS = ("name", "unit", "package", "package_size", "reorder_below", "match", "exclude")
# staples already on hand at setup (override with "pantry_on_hand" in config.json); everything else starts at zero until bought
ORIGINAL = set(config.C.get("pantry_on_hand", [])) or {"kosher_salt", "sea_salt", "black_pepper", "evoo", "neutral_oil", "sesame_oil", "red_wine_vinegar", "white_wine_vinegar",
            "cider_vinegar", "rice_vinegar", "cooking_spray", "flour", "sugar", "brown_sugar", "baking_powder", "baking_soda",
            "cornstarch", "vanilla", "honey", "maple_syrup", "cumin", "chili_powder", "smoked_paprika", "sweet_paprika",
            "garlic_powder", "onion_powder", "oregano", "thyme", "bay_leaves", "cinnamon", "red_pepper_flakes", "coriander",
            "turmeric", "garam_masala", "cayenne", "italian_seasoning", "soy_sauce", "dijon", "ketchup", "mayo", "hot_sauce",
            "chicken_broth", "white_rice", "butter"}

FRAC = {"½": .5, "¼": .25, "¾": .75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": .125, "⅜": .375, "⅝": .625, "⅞": .875}
QTY = re.compile(r"^\s*(?:about\s+|scant\s+|heaping\s+)?((?:\d+\s+)?\d+/\d+|\d+(?:\.\d+)?(?:\s*[½¼¾⅓⅔⅛⅜⅝⅞])?|[½¼¾⅓⅔⅛⅜⅝⅞])"
                 r"(?:\s*(?:-|–|to)\s*((?:\d+\s+)?\d+/\d+|\d+(?:\.\d+)?|[½¼¾⅓⅔⅛⅜⅝⅞]))?\s*"
                 r"(fl\.? oz|tsp|teaspoons?|tbsp|tablespoons?|cups?|ml|l|oz|ounces?|lbs?|pounds?|g|grams?|cloves?|sticks?)?\b\.?", re.I)


def num(s):
    s = s.strip()
    total = 0.0
    for part in s.split():
        if "/" in part:
            a, b = part.split("/"); total += float(a) / float(b)
        elif part[-1] in FRAC:
            total += (float(part[:-1]) if len(part) > 1 else 0) + FRAC[part[-1]]
        else:
            total += float(part)
    return total


def load():
    if os.path.exists(PANTRY):
        p = json.load(open(PANTRY)); p.setdefault("orders_seen", []); return p
    return {"updated": None, "tracking_since": dt.date.today().isoformat(), "deducted": [], "orders_seen": [], "items": {}}


def save(p):
    p["updated"] = dt.datetime.now().isoformat(timespec="minutes")
    json.dump(p, open(PANTRY, "w"), indent=1, ensure_ascii=False)
    lines = ["# PANTRY: generated from pantry.json (estimated levels). Edit by telling Claude, e.g. 'olive oil is full'.",
             "# The meal planner skips these when building the grocery list, and adds one to the cart when it runs low.", ""]
    for k, it in items_in_order(p):
        lines.append(f"{it['name']}: {level_text(it)}")
    open(PANTRY_TXT, "w").write("\n".join(lines) + "\n")


def items_in_order(p):
    order = {d[0]: i for i, d in enumerate(DEFAULTS)}
    return sorted(p["items"].items(), key=lambda kv: order.get(kv[0], 999))


def level_text(it):
    if it.get("status") == "unknown":
        return "on hand (not tracked until it appears in a confirmed order)"
    pct = max(0, it["on_hand"]) / it["package_size"] if it["package_size"] else 0
    u = it["unit"]
    amt = f"{it['on_hand']:.0f} {u}" if u != "tsp" else (f"{it['on_hand'] / 48:.1f} cups" if it["on_hand"] >= 48 else
                                                           f"{it['on_hand'] / 3:.0f} Tbsp" if it["on_hand"] >= 6 else f"{it['on_hand']:.0f} tsp")
    flag = " LOW" if it["on_hand"] <= it["reorder_below"] else ""
    src = {"tracked": "", "guess": " (starting guess)", "none": " (not stocked)", "unknown": ""}.get(it.get("status"), "")
    return f"~{amt} (~{pct:.0%} of a {it['package']}){flag}{src}"


def match_item(p, line):
    l = line.lower()
    for k, it in items_in_order(p):
        if re.search(it["match"], l) and not (it.get("exclude") and re.search(it["exclude"], l)):
            return k
    return None


def amount(it, key, line, group=""):
    """Amount of pantry item `it` that `line` uses, in the item's unit (None if unparseable)."""
    l = line.lower()
    m = QTY.match(l)
    if not m:
        if key in ("brown_rice", "white_rice") and ("serv" in l or "serv" in group.lower() or l.startswith(("prepared", "cooked"))):   # "cooked rice, for serving": ~1½ cups dry for the family
            return 1.5 * G_PER_CUP[key]
        if it["unit"] == "tsp" and re.search(r"to taste|pinch|dash|for (?:the )?pan|drizzle", l):
            return 0.5
        return None
    q = num(m.group(1))
    if m.group(2):
        q = (q + num(m.group(2))) / 2
    unit = (m.group(3) or "").lower().replace(".", "").rstrip("s").replace("fl oz", "fl oz")
    unit = {"teaspoon": "tsp", "tablespoon": "tbsp", "ounce": "oz", "pound": "lb", "gram": "g", "cup": "cup"}.get(unit, unit)
    if it["unit"] == "each":
        return q
    if it["unit"] == "tsp":
        if unit in ("tsp", "tbsp", "cup", "ml", "l", "fl oz"):
            return q * TSP[{"cup": "cup", "fl oz": "fl oz"}.get(unit, unit)]
        if unit == "oz":
            return q * 6
        if unit == "stick" and key == "butter":
            return q * 24
        if unit == "lb" and key == "butter":
            return q * 96
        if unit in ("g",):
            return q / 4.5
        return None
    # grams
    gpc = G_PER_CUP.get(key, 150)
    if unit == "cup": return q * gpc
    if unit == "tbsp": return q * gpc / 16
    if unit == "tsp": return q * gpc / 48
    if unit == "oz": return q * 28.35
    if unit == "lb": return q * 453.6
    if unit == "g": return q
    return None


def recipe_usage(p, recipe, scale=1.0):
    out = {}
    for group, items in recipe["ingredients"]:
        if re.match(r"\s*(optional|alternative|variation|substitute)", group or "", re.I):
            continue   # alternatives and optional extras aren't bought or used by default
        for line in items:
            if re.search(r"\boptional\b", line, re.I):
                continue
            k = match_item(p, line)
            if not k:
                continue
            a = amount(p["items"][k], k, line, group or "")
            if a is None:
                continue
            out[k] = out.get(k, 0) + a * scale
    return out


def plan_meals(plan):
    """(date, meal, recipe id, scale) for every planned meal in a plan."""
    meals = []
    bl = plan["breakfast_lunch"]
    for d in plan["days"]:
        din = d["dinner"]
        if not din.get("rest"):
            meals.append((d["date"], "dinner", din["id"], float(din.get("scale", 1) or 1)))
    # breakfast/lunch are batch-prepped Sunday: charge each batch to the plan's first day
    first = plan["days"][0]["date"]
    meals.append((first, "breakfast", bl["breakfast"], float(bl.get("breakfast_batches", 1) or 1)))
    meals.append((first, "lunch", bl["lunch"], float(bl.get("lunch_batches", 1) or 1)))
    return meals


def usage_for(p, cat, plan):
    tot = {}
    for _date, _meal, rid, scale in plan_meals(plan):
        for k, a in recipe_usage(p, cat[rid], scale).items():
            tot[k] = tot.get(k, 0) + a
    return tot


def catalog():
    sys.path.insert(0, HERE)
    import planner
    return planner.catalog()


def history_plans():
    hist = json.load(open(os.path.join(config.STATE, "history.json"))) if os.path.exists(os.path.join(config.STATE, "history.json")) else []
    return [json.load(open(os.path.join(ROOT, w["plan"]))) for w in hist]


def init():
    p = load()
    for row in DEFAULTS:
        k = row[0]
        d = dict(zip(FIELDS, row[1:]))
        it = p["items"].get(k)
        if it is None:
            # an item nobody has told us about: assume a partly used package
            p["items"][k] = {**d, "on_hand": d["package_size"] if k in ORIGINAL else 0,
                             "status": "unknown" if k in ORIGINAL else "none", "last_restock": None}
        else:
            for f in ("name", "unit", "match", "exclude", "reorder_below", "package", "package_size"):
                it[f] = d[f]
    save(p)
    return p


def deduct(p, cat, before):
    logged = {}
    lp = os.path.join(config.STATE, "cook_log.json")
    for e in (json.load(open(lp)) if os.path.exists(lp) else []):
        logged[(e["date"], e.get("meal", "dinner"))] = e.get("status", "cooked")
    done = set(p["deducted"])
    applied = []
    for plan in history_plans():
        for date, meal, rid, scale in plan_meals(plan):
            key = f"{date}:{meal}"
            if date >= before or key in done:
                continue
            if logged.get((date, meal)) in ("skipped", "moved"):
                p["deducted"].append(key); continue
            for k, a in recipe_usage(p, cat[rid], scale).items():
                if p["items"][k].get("status") == "unknown":
                    continue
                p["items"][k]["on_hand"] = round(p["items"][k]["on_hand"] - a, 1)
            p["deducted"].append(key); applied.append(f"{key} {cat[rid]['title']}")
    save(p)
    print(f"DEDUCTED {len(applied)} meal(s)" + ("".join(f"\n  {a}" for a in applied)))


def pending_usage(p, cat, through=None):
    """Usage of planned meals not yet deducted (optionally only those on/before `through`)."""
    done = set(p["deducted"]); tot = {}
    for plan in history_plans():
        for date, meal, rid, scale in plan_meals(plan):
            if f"{date}:{meal}" in done or (through and date > through):
                continue
            for k, a in recipe_usage(p, cat[rid], scale).items():
                tot[k] = tot.get(k, 0) + a
    return tot


def check(p, cat, plan):
    """LOW items: estimated level after every planned-but-not-yet-deducted meal (including this plan) is under reorder."""
    end = plan["days"][-1]["date"]
    need = pending_usage(p, cat, through=end)
    if plan["week_start"] not in {pl["week_start"] for pl in history_plans()}:   # plan not rendered yet
        for k, a in usage_for(p, cat, plan).items():
            need[k] = need.get(k, 0) + a
    lows = []
    for k, it in items_in_order(p):
        if it.get("status") == "unknown":
            continue
        after = it["on_hand"] - need.get(k, 0)
        # reorder only what a planned meal needs, or a staple kept on hand all the time
        if after <= it["reorder_below"] and (need.get(k, 0) > 0 or k in ORIGINAL):
            lows.append((k, it, after))
    for k, it, after in lows:
        print(f"LOW\t{k}\t{it['name']}\tbuy 1 {it['package']}\test. left after this plan: {max(after, 0):.0f} {it['unit']}"
              + {"guess": "\t(starting guess, so confirm it)", "none": "\t(not stocked yet)"}.get(it.get("status"), ""))
    if not lows:
        print("OK: nothing in the pantry should run low this week")


def restock(p, keys, order=None):
    if order and order in p["orders_seen"] and not keys:
        return
    for k in keys:
        it = p["items"][k]
        base = 0 if it.get("status") == "unknown" else max(it["on_hand"], 0)
        it["on_hand"] = round(base + it["package_size"], 1)
        it["status"] = "tracked"; it["last_restock"] = dt.date.today().isoformat()
        print(f"restocked {k}: {level_text(it)}")
    if order and order not in p["orders_seen"]:
        p["orders_seen"].append(order)
    save(p)


def set_level(p, k, level):
    it = p["items"][k]
    it["on_hand"] = {"full": it["package_size"], "half": it["package_size"] / 2, "low": it["reorder_below"],
                     "empty": 0}.get(level, None) if level in ("full", "half", "low", "empty") else float(level)
    it["status"] = "tracked"
    save(p); print(f"{k}: {level_text(it)}")


def sheet(wb):
    """Add a Pantry tab to an openpyxl workbook (called by cooklog.build_xlsx)."""
    from openpyxl.styles import Font, PatternFill, Alignment
    if not os.path.exists(PANTRY):
        return
    p = load(); ws = wb.create_sheet("Pantry")
    ws.append(["Item", "Estimated left", "Level", "Package", "Reorder when below", "Last restocked", "Source"])
    for k, it in items_in_order(p):
        pct = max(0, it["on_hand"]) / it["package_size"] if it["package_size"] else 0
        ws.append([it["name"], level_text(it).split(" (")[0].lstrip("~"), pct, it["package"],
                   f"{it['reorder_below']} {it['unit']}", it.get("last_restock") or "",
                   {"tracked": "Tracked (confirmed orders)", "guess": "Starting guess", "none": "Not stocked", "unknown": "On hand, untracked"}.get(it.get("status"), "")])
    for c in ws[1]:
        c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="7A2331")
    for row in ws.iter_rows(min_row=2):
        row[2].number_format = "0%"
        if row[2].value is not None and row[2].value <= 0.2:
            row[2].fill = PatternFill("solid", fgColor="F4CCCC")
    for col, w in zip("ABCDEFG", [30, 16, 9, 22, 18, 14, 15]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"


if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("help", [])
    if cmd == "help":
        print(__doc__); sys.exit()
    if cmd == "reset":
        if os.path.exists(PANTRY):
            os.remove(PANTRY)
        init(); print("pantry reset: staples untracked, nothing deducted, no orders applied"); sys.exit()
    p = init()
    if cmd == "status":
        for k, it in items_in_order(p):
            print(f"{k:20} {it['name']:30} {level_text(it)}")
    elif cmd == "skip-list":
        for k, it in items_in_order(p):
            if it["on_hand"] > it["reorder_below"]:
                print(it["name"])
    elif cmd == "usage":
        cat = catalog(); plan = json.load(open(args[0]))
        for k, a in sorted(usage_for(p, cat, plan).items()):
            print(f"{k:20} {a:8.1f} {p['items'][k]['unit']}")
    elif cmd == "check":
        check(p, catalog(), json.load(open(args[0])))
    elif cmd == "restock":
        order = None
        if "--order" in args:
            i = args.index("--order"); order = args[i + 1]; del args[i:i + 2]
        if order and order in p["orders_seen"]:
            print(f"ALREADY_APPLIED order {order}")
        else:
            restock(p, args, order)
    elif cmd == "since":   # orders before this date are never applied (Gmail query: after:YYYY/MM/DD)
        print(p.get("tracking_since", dt.date.today().isoformat()).replace("-", "/"))
    elif cmd == "order-seen":
        print("SEEN" if args[0] in p["orders_seen"] else "NEW")
    elif cmd == "match":
        print(match_item(p, " ".join(args)) or "NONE")
    elif cmd == "reset":
        if os.path.exists(PANTRY):
            os.remove(PANTRY)
        init(); print("pantry reset: staples untracked, nothing deducted, no orders applied")
    elif cmd == "unstock":   # a restock that was dropped from the cart before it was bought
        for k in args:
            it = p["items"][k]; it["on_hand"] = round(it["on_hand"] - it["package_size"], 1)
            if it["on_hand"] <= 0 and k not in ORIGINAL:
                it["on_hand"], it["status"] = 0, "none"
            print(f"unstocked {k}: {level_text(it)}")
        save(p)
    elif cmd == "deduct":
        deduct(p, catalog(), args[0] if args else dt.date.today().isoformat())
    elif cmd == "set":
        set_level(p, args[0], args[1])
    else:
        print(__doc__)
