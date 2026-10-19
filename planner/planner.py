"""Helpers for the weekly meal-plan agent (all personal settings come from config.json).

Commands (run with python3 from anywhere):
  planner.py catalog              rebuild the recipe catalog from recipes_dir
  planner.py candidates [START]   candidate pools for the week starting Monday START (default: next Monday)
  planner.py weather              16-day forecast for the configured location (Open-Meteo, worldwide)
  planner.py ingredients ID ...   published ingredient lists for these recipe ids
  planner.py render PLAN.json     build the plan PDF, email.html and text.txt next to PLAN.json; log the week to history
  planner.py tonight [DATE]       tonight's dinner as JSON
  planner.py tonight-text [DATE]  the 4 PM iMessage for DATE (or NOTHING); send it with imessage.py --file
  planner.py log add '<json>'     add a cook-log entry (see cooklog.py)
  planner.py log sync DIR         log new feedback saved on the Kitchen Log page (DIR = ArtifactData list out_dir)
  planner.py log xlsx             rebuild Cook_Log.xlsx
  planner.py feedback-plan        JSON body for the Kitchen Log page's plan/current doc (last 7 days + newest plan, with recipes)
  planner.py cart-text PLAN.json [N]  write cart_text.txt / cart_text2.txt (the "order N is in your cart" iMessage)
  planner.py order-list PLAN.json N   BUY/DROP lines for order N, skip-aware
  planner.py pdfs-needed          recipe PDFs for the Kitchen Log window not yet uploaded to the page (id<TAB>path)
  planner.py pdf-asset ID BLOB    record that recipe ID's PDF was uploaded as asset BLOB
  planner.py spend add ORDER DATE AMOUNT   record a confirmed grocery order's total (from its confirmation email)
  planner.py spend [DATE]         grocery spending for that week and the week before
  planner.py recap [DATE]         the 7 days before DATE: planned dinners vs. cook log
"""
import datetime as dt, glob, json, os, re, subprocess, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, recipes, cooklog

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = config.DATA                     # plans and logs live under the configured data_dir
PLANS = config.PLANS
CATALOG = os.path.join(config.STATE, "catalog.json")
HISTORY = os.path.join(config.STATE, "history.json")
REPEAT_WEEKS = 3
FEEDBACK_URL = config.KITCHEN_LOG_URL  # your Kitchen Log page (recipe + rating), if you published one
PDF_ASSETS = os.path.join(config.STATE, "pdf_assets.json")  # recipe id -> {"asset": blob id, "mtime": pdf mtime when uploaded}
DINNER_POOLS = config.POOLS
O1, O2 = config.ORDERS.get("order1_day", "Sunday"), config.ORDERS.get("order2_day", "Thursday")
O2_FILL = config.ORDERS.get("order2_fill_day", "Wednesday")
_span = config.ORDERS.get("order2_dinners", ["Fri", "Sat", "Sun"])
O2_SPAN = f"{_span[0]}–{_span[-1]}"


def display_path(p):
    """A readable location for a file (relative to the folder that holds data_dir)."""
    rel = os.path.relpath(p, os.path.dirname(ROOT))
    return " › ".join(rel.split(os.sep))


# ------------------------------------------------------------------ catalog
def build_catalog():
    out = []
    for e in recipes.load():
        if e["folder"] == config.LESSON_FOLDER:
            e["syllabus"] = {"module": e["section"], "done": None}
        out.append(e)
    with open(CATALOG, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"catalog.json: {len(out)} recipes")


def catalog():
    if not os.path.exists(CATALOG) or os.path.getmtime(CATALOG) < recipes.newest_mtime():
        build_catalog()
    cat = {r["id"]: r for r in json.load(open(CATALOG))}
    for r in cat.values():
        r["pdf_location"] = r.get("pdf_label", "")
    st = cooklog.stats(cat)
    for r in cat.values():
        if r["title"] in st:
            r["log"] = st[r["title"]]
    return cat


def history():
    return json.load(open(HISTORY)) if os.path.exists(HISTORY) else []


def next_monday(d=None):
    d = d or dt.date.today()
    return d + dt.timedelta(days=(7 - d.weekday()) % 7 or 7)


def cs_sort_key(i):
    """Natural order for lesson ids like CS-1.2 or L-10."""
    return [int(n) for n in re.findall(r"\d+", i)] or [0]


# ------------------------------------------------------------------ candidates
def candidates(start):
    cat = catalog(); hist = history()
    cutoff = start - dt.timedelta(weeks=REPEAT_WEEKS)
    recent_dinners, used_bl, scheduled_cs, skipped_cs = set(), [], set(), set()
    for w in hist:
        ws = dt.date.fromisoformat(w["week_start"])
        if ws >= start:
            continue
        if ws >= cutoff:
            recent_dinners.update(w.get("dinners", []))
    log = cooklog.load()
    skipped_ids = {e["id"] for e in log if e.get("status") in ("skipped", "moved")}
    cooked_ids = {e["id"] for e in log if e.get("status", "cooked") == "cooked"}
    recent_dinners -= {i for i in skipped_ids if i not in cooked_ids}
    # the same dish is cross-listed under several ids (e.g. CORE-15 = ITJ-01), so block repeats by title too
    recent_titles = {cat[i]["title"] for i in recent_dinners if i in cat}
    recent_dinners |= {i for i, r in cat.items() if r["title"] in recent_titles}
    for w in hist:
        ws = dt.date.fromisoformat(w["week_start"])
        if ws >= start:
            continue
        used_bl.append((ws, w.get("breakfast"), w.get("lunch")))
        if w.get("cs_lesson"):
            scheduled_cs.add(w["cs_lesson"])
        skipped_cs.update(w.get("cs_skipped", []))
    skipped_cs |= {i for i in skipped_ids if config.is_lesson(i, cat) and i not in cooked_ids}
    # next lesson: first not logged as cooked and not already scheduled in a past plan (a logged skip re-queues it)
    cs = sorted((r for r in cat.values() if config.LESSON_FOLDER and r["folder"] == config.LESSON_FOLDER), key=lambda r: cs_sort_key(r["id"]))
    nxt = None
    for r in cs:
        done = (r.get("syllabus") or {}).get("done")
        if done == "Y" or r["id"] in cooked_ids:
            continue
        if r["id"] in scheduled_cs and done != "N" and r["id"] not in skipped_cs:
            continue
        nxt = r; break

    def line(r):
        lg = r.get("log")
        if lg and lg["avg"] is not None:
            rating = f' ★{lg["avg"]} {lg["tier"].upper()} (made {lg["n"]}x)'
        elif r.get("rating"):
            rating = f' ★{r["rating"]}'
        else:
            rating = ""
        return f'{r["id"]:10} {r["title"][:58]:58} | {r["cuisine"] or "":22} | prep {r["prep"] or "?":8} total {r["total"] or "?":10} | {r["difficulty"]}{rating}'

    print(f"WEEK {start} → {start + dt.timedelta(days=6)}   (repeat window: dinners since {cutoff})")
    print(f"\n== NEXT {config.LESSON_LABEL.upper()} LESSON ==")
    if nxt:
        print(line(nxt)); print("   ", nxt["syllabus"]["module"])
        print("    skills:", ", ".join(nxt["skills"] or []))
        print("    make-ahead:", nxt.get("ahead") or "—")
        following = cs[cs.index(nxt) + 1: cs.index(nxt) + 3]
        if following:
            print("    (following lessons:", ", ".join(f'{r["id"]} {r["title"]}' for r in following), ")")
    else:
        print("All lessons complete!")
    for pool, folders in DINNER_POOLS.items():
        print(f"\n== DINNER POOL: {pool} ({', '.join(folders)}) — excluding dinners used in the last {REPEAT_WEEKS} weeks and DROP-tier dishes; FAVORITE/KEEPER first ==")
        def score(r):
            lg = r.get("log") or {}
            return -(lg.get("avg") or r.get("rating") or 0)
        for r in sorted((r for r in cat.values() if r["folder"] in folders and r["id"] not in recent_dinners
                         and (r.get("log") or {}).get("tier") != "Drop"), key=lambda r: (score(r), r["id"])):
            if r["folder"].startswith("Hosting_") and r["section"] != "Mains":
                continue
            if r["folder"] == "Date_night" and r["section"] == "Desserts":
                continue
            print(" ", line(r))
    last_bl = {x for _, b, l in sorted(used_bl)[-1:] for x in (b, l) if x}
    for label, pool in (("BREAKFAST", config.BREAKFAST), ("LUNCH", config.LUNCH)):
        print(f"\n== {label} ({pool['folder']} › {pool['section']}) (✗ = used last week, don't repeat) ==")
        for r in sorted((r for r in cat.values() if r["folder"] == pool["folder"] and r["section"] == pool["section"]), key=lambda r: r["id"]):
            mark = "✗" if r["id"] in last_bl else " "
            uses = sum(1 for _, b, l in used_bl if r["id"] in (b, l))
            print(f" {mark} {line(r)}  (used {uses}x)")
            print(f"      keeps: {(r.get('ahead') or '—')[:160]}")
            print(f"      portion: {(r.get('nutrition') or '—')[:160]}")
            if (r.get("log") or {}).get("tier") == "Drop":
                print("      DROP: rated low in the cook log; don't pick it")


# ------------------------------------------------------------------ weather
WMO = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Cloudy", 45: "Fog", 48: "Freezing fog", 51: "Light drizzle",
       53: "Drizzle", 55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle", 61: "Light rain", 63: "Rain",
       65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
       77: "Snow grains", 80: "Rain showers", 81: "Rain showers", 82: "Heavy showers", 85: "Snow showers",
       86: "Heavy snow showers", 95: "Thunderstorms", 96: "Thunderstorms with hail", 99: "Thunderstorms with hail"}


def weather():
    """16-day daily forecast from Open-Meteo (free, worldwide, no key), enough to cover the whole plan week."""
    metric = config.C["location"].get("units", "imperial") == "metric"
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={config.LAT}&longitude={config.LON}"
           "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code"
           f"&temperature_unit={'celsius' if metric else 'fahrenheit'}&timezone=auto&forecast_days=16")
    try:
        out = subprocess.run(["curl", "-s", "-m", "20", url], capture_output=True, text=True).stdout
        d = json.loads(out)["daily"]
    except Exception:
        print(f"Forecast unavailable; fall back to a web search for the {config.PLACE} forecast or seasonal norms.")
        return
    u = "C" if metric else "F"
    print(f"Forecast for {config.PLACE} (Open-Meteo):")
    for i, day in enumerate(d["time"]):
        dd = dt.date.fromisoformat(day)
        rain = d["precipitation_probability_max"][i]
        print(f"{dd:%a %b %-d}  high {round(d['temperature_2m_max'][i]):>3}°{u}  low {round(d['temperature_2m_min'][i]):>3}°{u}  "
              f"{WMO.get(d['weather_code'][i], 'Mixed'):<22} {'' if rain is None else f'{rain}% chance of precipitation'}")


def ingredients(ids):
    cat = catalog()
    for i in ids:
        r = cat[i]
        print(f'\n### {i} {r["title"]} — serves {r["serves"]}')
        if r.get("adapted"):
            print("scaling note:", r["adapted"])
        for g, items in r["ingredients"]:
            print(f"  [{g}]")
            for it in items:
                print("   -", it)


# ------------------------------------------------------------------ render
def render(plan_path):
    from pdfstyle import S, WINE, INK, MUTED, CREAM, SAGE, SAGE_D, RULE, W, esc, boxed
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak, KeepTogether, Paragraph
    from reportlab.lib.styles import ParagraphStyle
    P = lambda t, st="body": Paragraph(t, S[st])  # raw markup: every data string below is esc()'d explicitly
    LESSON = config.LESSON_LABEL
    plan = json.load(open(plan_path))
    cat = catalog()
    outdir = os.path.dirname(os.path.abspath(plan_path))
    start = dt.date.fromisoformat(plan["week_start"])

    def link(rid):
        r = cat[rid]
        # the web link works on any device; the PDF location is listed under each dinner
        if not r.get("url"):
            return f'<b>{esc(r["title"])}</b>'
        return f'<link href="{r["url"]}" color="#7A2331"><u>{esc(r["title"])}</u></link>'

    flow = [P(f"WEEKLY MEAL PLAN · {start:%b %-d} – {(start + dt.timedelta(days=6)):%b %-d, %Y}".upper(), "kicker"),
            P("This Week at the Table", "title"), P(esc(plan.get("summary", "")), "native")]
    if plan.get("recap"):
        flow.append(P("Last week, from your cook log", "h2"))
        flow += [P("• " + esc(x), "item") for x in plan["recap"]]
    if plan.get("alerts"):
        flow.append(boxed([P("<b>Plan-ahead alerts</b>", "boxh")] + [P("• " + esc(a), "box") for a in plan["alerts"]]))
        flow.append(Spacer(1, 8))
    rows = [[P("<b>Day</b>", "h3"), P("<b>Dinner</b>", "h3"), P("<b>Why this night</b>", "h3")]]
    for d in plan["days"]:
        date = dt.date.fromisoformat(d["date"])
        din = d["dinner"]
        if din.get("rest"):
            dish = P((f"<b>Leftovers:</b> {esc(cat[din['leftovers_of']]['title'])}" if din.get("leftovers_of") else "<b>Rest night</b>")
                     + " · " + esc(din.get("note", "leftovers or takeout")), "body")
        else:
            tag = f" <font color='#4F6B45'><b>[{esc(LESSON)}]</b></font>" if config.is_lesson(din["id"], cat) else ""
            dish = P(f'{link(din["id"])}{tag}<br/><font size="8" color="#6B645C">{("PDF: " + esc(cat[din["id"]]["pdf_location"]) + "<br/>") if cat[din["id"]].get("pdf_location") else ""}prep {esc(cat[din["id"]]["prep"] or "?")} · total {esc(cat[din["id"]]["total"] or "?")}</font>', "body")
        rows.append([P(f"<b>{date:%a}</b><br/>{date:%b %-d}", "body"), dish, P(esc(d.get("reason", "")) + (f'<br/><i>{esc(d["weather"])}</i>' if d.get("weather") else ""), "small")])
    t = Table(rows, colWidths=[0.8 * inch, 3.2 * inch, W - 4.0 * inch])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
                           ("BACKGROUND", (0, 0), (-1, 0), CREAM), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    flow += [P(f"Dinners ({esc(config.HOUSEHOLD)} · about {config.SERVINGS} servings)", "h2"), t]
    bl = plan["breakfast_lunch"]
    flow += [P(f"{esc(config.NAME)}'s breakfast &amp; lunch", "h2"),
             P(f'<b>Breakfast ×7:</b> {link(bl["breakfast"])} — {esc(bl.get("breakfast_note", ""))}', "body"),
             P(f'<b>Lunch ×5 (Mon–Fri):</b> {link(bl["lunch"])} — {esc(bl.get("lunch_note", ""))}', "body")]
    if plan.get("prep_schedule"):
        flow.append(P("Prep schedule", "h2"))
        for p in plan["prep_schedule"]:
            flow.append(P(f'<b>{esc(p["when"])}:</b> {esc(p["task"])}', "item"))
    flow += [PageBreak(), P("GROCERY LIST · WHOLE FOODS DELIVERY " + esc(plan.get("delivery", "")).upper(), "kicker"),
             P("Shopping List", "title")]
    if plan.get("cart_status"):
        flow.append(boxed([P("<b>Whole Foods cart</b>", "boxh"), P(esc(plan["cart_status"]), "box")]
                          + ([P(esc(plan["cart_details"]), "box")] if plan.get("cart_details") else [])))
        flow.append(Spacer(1, 6))
    orders = sorted({i.get("order", 1) for a in plan["groceries"] for i in a["items"]})
    for o in orders:
        if len(orders) > 1:
            flow.append(P(esc({1: f"Order 1 · arrives {O1} (early-week dinners, breakfasts & lunches, pantry)",
                               2: f"Order 2 · arrives {O2} ({O2_SPAN} dinners; filled {O2_FILL})"}.get(o, f"Order {o}")), "h2"))
            if o == 2 and plan.get("cart2_status"):
                flow.append(P(esc(plan["cart2_status"]), "small"))
        for aisle in plan["groceries"]:
            its = [i for i in aisle["items"] if i.get("order", 1) == o]
            if not its:
                continue
            items = [P(f'☐ <b>{esc(i["item"])}</b> — {esc(i["qty"])}' + (f' <font color="#6B645C" size="7.5">({esc(i["for"])})</font>' if i.get("for") else ""), "item") for i in its]
            flow.append(KeepTogether([P(esc(aisle["aisle"]), "h3")] + items))
    if plan.get("pantry_alerts"):
        flow += [P("Pantry running low (added to the cart)", "h2")] + [P("• " + esc(a), "item") for a in plan["pantry_alerts"]]
    if plan.get("pantry_check"):
        flow += [P("From your pantry this week (not ordered)", "h2"), P(esc(", ".join(plan["pantry_check"])), "small")]
    if plan.get("buy_fresh_later"):
        flow += [P("Buy fresh later in the week", "h2")] + [P("• " + esc(x), "item") for x in plan["buy_fresh_later"]]
    flow += [Spacer(1, 10), P("Recipe titles open the published recipe online; your PDF of each recipe is listed under each dinner.", "small")]
    pdf = os.path.join(outdir, f"Meal_Plan_{start:%Y-%m-%d}.pdf")
    SimpleDocTemplate(pdf, pagesize=letter, leftMargin=0.65 * inch, rightMargin=0.65 * inch, topMargin=0.6 * inch,
                      bottomMargin=0.6 * inch, title=f"Meal Plan {start}").build(flow)

    # email HTML
    def elink(rid):
        r = cat[rid]
        return f'<a href="{r["url"]}">{r["title"]}</a>' if r.get("url") else f'<b>{r["title"]}</b>'
    h = [f'<h2 style="color:#7A2331;font-family:Georgia">Meal plan · {start:%b %-d} – {(start + dt.timedelta(days=6)):%b %-d}</h2>',
         f'<p>{plan.get("summary", "")}</p>']
    if plan.get("recap"):
        h.append("<h3>Last week, from your cook log</h3><ul>" + "".join(f"<li>{x}</li>" for x in plan["recap"]) + "</ul>")
    if plan.get("cart_status"):
        h.append(f'<p style="background:#F6F1E9;padding:8px"><b>Whole Foods cart:</b> {plan["cart_status"]}'
                 + (f'<br/>{plan["cart_details"]}' if plan.get("cart_details") else "") + "</p>")
    if plan.get("alerts"):
        h.append("<h3>Plan-ahead alerts</h3><ul>" + "".join(f"<li>{a}</li>" for a in plan["alerts"]) + "</ul>")
    h.append('<h3>Dinners</h3><table cellpadding="5" style="border-collapse:collapse">')
    for d in plan["days"]:
        date = dt.date.fromisoformat(d["date"]); din = d["dinner"]
        dish = (f'<b>Leftovers:</b> {cat[din["leftovers_of"]]["title"]} — {din.get("note", "")}' if din.get("leftovers_of") else
                f'<b>Rest night</b> — {din.get("note", "leftovers or takeout")}') if din.get("rest") else elink(din["id"]) + (f" <i>({LESSON})</i>" if config.is_lesson(din["id"], cat) else "")
        h.append(f'<tr style="border-bottom:1px solid #D9CFC1"><td><b>{date:%a %-m/%-d}</b></td><td>{dish}</td><td style="color:#6B645C">{d.get("reason", "")}</td></tr>')
    h.append("</table>")
    h.append(f'<h3>Your breakfast &amp; lunch</h3><p>Breakfast ×7: {elink(bl["breakfast"])}<br/>Lunch ×5: {elink(bl["lunch"])}</p>')
    if plan.get("prep_schedule"):
        h.append("<h3>Prep schedule</h3><ul>" + "".join(f'<li><b>{p["when"]}:</b> {p["task"]}</li>' for p in plan["prep_schedule"]) + "</ul>")
    # grocery list lives in the email body so no attachment is needed (the connector can't carry the PDF)
    h.append("<h3>Grocery list</h3>")
    for aisle in plan["groceries"]:
        h.append(f'<p style="margin:8px 0 2px"><b>{aisle["aisle"]}</b></p><ul style="margin-top:0">'
                 + "".join(f'<li>{i["item"]}: {i["qty"]}' + (f' <span style="color:#6B645C">({i["for"]})</span>' if i.get("for") else "") + "</li>" for i in aisle["items"]) + "</ul>")
    if plan.get("pantry_check"):
        h.append(f'<p><b>Pantry check (not ordered):</b> {", ".join(plan["pantry_check"])}</p>')
    if plan.get("buy_fresh_later"):
        h.append("<p><b>Buy fresh later in the week:</b></p><ul>" + "".join(f"<li>{x}</li>" for x in plan["buy_fresh_later"]) + "</ul>")
    h.append(f'<p style="color:#6B645C">Plan PDF: {display_path(pdf)}</p>')
    open(os.path.join(outdir, "email.html"), "w").write("\n".join(h))

    # iMessage version (plain text, phone-sized)
    t = [f"🍽️ Meal plan · week of {start:%b %-d}"]
    if plan.get("recap"):
        t += ["", "Last week:"] + [f"• {x}" for x in plan["recap"]]
    t.append("")
    for d in plan["days"]:
        date = dt.date.fromisoformat(d["date"]); din = d["dinner"]
        dish = (f"Leftovers 🍲 ({cat[din['leftovers_of']]['title']})" if din.get("leftovers_of") else "Rest night 😌") if din.get("rest") else cat[din["id"]]["title"] + (f" ({LESSON})" if config.is_lesson(din["id"], cat) else "")
        t.append(f"{date:%a}: {dish}")
    t += ["", f"Breakfast: {cat[bl['breakfast']]['title']}", f"Lunch: {cat[bl['lunch']]['title']}"]
    if plan.get("alerts"):
        t += ["", "Heads-up:"] + [f"• {a}" for a in plan["alerts"]]
    if plan.get("pantry_alerts"):
        t += ["", "🧂 Pantry running low (adding to cart):"] + [f"• {a}" for a in plan["pantry_alerts"]]
    two = any(i.get("order", 1) == 2 for a in plan.get("groceries", []) for i in a["items"])
    if plan.get("cart_pending"):
        t += ["", f"🛒 Order 1 (arrives {O1}): adding it to your cart now. I'll text you when it's all in."
              if two else "🛒 Adding groceries to your cart now. I'll text you when they're all in."]
    elif plan.get("cart_status"):
        t += ["", f"🛒 {'Order 1: ' if two else ''}{plan['cart_status']}"]
    if two:
        t.append(f"🛒 Order 2 ({O2_SPAN} dinners, {O2} delivery): I'll fill it {O2_FILL}, after checking for skipped meals.")
    t += ["", f"Full plan + grocery list: {display_path(pdf)}"] + ([f"Rate meals anytime: {FEEDBACK_URL}"] if FEEDBACK_URL else [])
    open(os.path.join(outdir, "text.txt"), "w").write("\n".join(t))

    # log to history (replace any existing entry for this week)
    hist = [w for w in history() if w["week_start"] != plan["week_start"]]
    dinners = [d["dinner"]["id"] for d in plan["days"] if not d["dinner"].get("rest")]
    hist.append({"week_start": plan["week_start"], "dinners": dinners, "breakfast": bl["breakfast"], "lunch": bl["lunch"],
                 "cs_lesson": next((x for x in dinners if config.is_lesson(x, cat)), None), "plan": os.path.relpath(plan_path, ROOT)})
    hist.sort(key=lambda w: w["week_start"])
    json.dump(hist, open(HISTORY, "w"), indent=1)
    print("PDF:", pdf); print("EMAIL:", os.path.join(outdir, "email.html")); print("TEXT:", os.path.join(outdir, "text.txt")); print("history.json updated")


def tonight(date):
    cat = catalog()
    for w in reversed(history()):
        plan = json.load(open(os.path.join(ROOT, w["plan"])))
        for d in plan["days"]:
            if d["date"] == date.isoformat():
                din = d["dinner"]
                tomorrow = date + dt.timedelta(days=1)
                ahead = [p for p in plan.get("prep_schedule", []) if date.isoformat() in p.get("dates", [])]
                if din.get("rest"):
                    print(json.dumps({"date": d["date"], "rest": True, "note": din.get("note"), "prep_tonight": ahead}, indent=1, ensure_ascii=False))
                    return
                r = cat[din["id"]]
                print(json.dumps({"date": d["date"], "id": r["id"], "title": r["title"], "url": r["url"], "source": r["source"],
                                  "pdf_location": r["pdf_location"], "prep": r["prep"], "total": r["total"],
                                  "scale_note": din.get("scale_note"), "start_note": din.get("start_note"),
                                  "prep_tonight": ahead, "tomorrow": tomorrow.isoformat(),
                                  "last_time": ({k: r["log"][k] for k in ("last_date", "last_rating", "last_change", "last_change_date")}
                                                if r.get("log") else None)}, indent=1, ensure_ascii=False))
                return
    print("NO_PLAN")


def config_is_lesson(rid, cat):
    return config.is_lesson(rid, cat)


def skip_rescue(date, cat):
    """Lines for the 4 PM text: dinners skipped in the last 2 days whose fresh meat/fish should be frozen now."""
    lp = os.path.join(os.path.dirname(cooklog.LOG), os.path.basename(cooklog.LOG))
    out = []
    for e in (json.load(open(lp)) if os.path.exists(lp) else []):
        if e.get("status") != "skipped" or e.get("meal", "dinner") != "dinner" or e.get("id") not in cat:
            continue
        d = dt.date.fromisoformat(e["date"])
        if not (date - dt.timedelta(days=2) <= d < date):
            continue
        lines = " ".join(l.lower() for _, items in cat[e["id"]]["ingredients"] for l in items)
        if re.search(r"chicken|beef|pork|turkey|lamb|salmon|fish|shrimp|cod|sausage|steak|thigh|breast", lines):
            fishy = re.search(r"salmon|fish|shrimp|cod|scallop|mussel", lines)
            out.append(f"You skipped {d:%A}'s {cat[e['id']]['title']}: " +
                       ("cook or freeze its seafood today; it won't keep." if fishy else
                        "freeze its meat tonight so it keeps. On Wednesday I'll move the dish to a later night."))
    return out


def tonight_text(date):
    """The 4 PM iMessage for DATE, or NOTHING when there's nothing to send."""
    cat = catalog()
    rescue = skip_rescue(date, cat)
    for w in reversed(history()):
        plan = json.load(open(os.path.join(ROOT, w["plan"])))
        for d in plan["days"]:
            if d["date"] != date.isoformat():
                continue
            din = d["dinner"]
            ahead = rescue + [p["task"] for p in plan.get("prep_schedule", []) if date.isoformat() in p.get("dates", [])]
            # tomorrow's lesson: send its technique videos the evening before
            tmr = next((x["dinner"] for x in plan["days"] if x["date"] == (date + dt.timedelta(days=1)).isoformat()), None)
            if tmr and not tmr.get("rest") and config_is_lesson(tmr["id"], cat) and cat[tmr["id"]].get("videos"):
                ahead += [f"Watch tonight for tomorrow's lesson: {v['title']}" + (f" ({v['length']})" if v.get("length") else "") + f" {v['url']}"
                          for v in cat[tmr["id"]]["videos"][:2]]
            if din.get("rest") and din.get("leftovers_of"):
                t = [f"🍲 Leftovers tonight: {cat[din['leftovers_of']]['title']}. No cooking."]
                if din.get("note"):
                    t.append(din["note"])
                if ahead:
                    t += ["", "Prep tonight for later this week:"] + [f"• {a}" for a in ahead]
                print("\n".join(t)); return
            if din.get("rest"):
                if not ahead:
                    print("NOTHING"); return
                print("\n".join(["🍽️ Rest night tonight, no cooking 😌", "", "Prep tonight for later this week:"] + [f"• {a}" for a in ahead]))
                return
            r = cat[din["id"]]
            t = [f"🍽️ Tonight: {r['title']}" + (f" ({config.LESSON_LABEL})" if config.is_lesson(r["id"], cat) else "")]
            lg = r.get("log")
            if lg and lg.get("last_change") and (lg.get("last_change_date") or "") < date.isoformat():
                star = f", ★{lg['last_rating']:g}" if lg.get("last_rating") else ""
                t.append(f"Last time ({dt.date.fromisoformat(lg['last_change_date']):%b %-d}{star}): {lg['last_change']}")
            t.append(f"⏱ Prep {r['prep']} · total {r['total']}")
            if din.get("start_note"):
                t.append(f"Start: {din['start_note']}")
            if din.get("scale_note"):
                t.append(din["scale_note"])
            vids = r.get("videos") or []
            if vids:
                t += [""] + [f"▶ Watch: {v['title']}" + (f" ({v['length']})" if v.get("length") else "") + f"\n{v['url']}" for v in vids[:2]]
            if r.get("url"):
                t += ["", f"Original recipe: {r['url']}"]
            if ahead:
                t += ["", "Prep tonight for later this week:"] + [f"• {a}" for a in ahead]
            if FEEDBACK_URL:
                t += ["", f"Your recipe + rate it after dinner: {FEEDBACK_URL}#{date.isoformat()}"]
            print("\n".join(t)); return
    # a prep day outside the plan's Mon–Sun (e.g. Sunday batch prep after delivery)
    for w in reversed(history()):
        plan = json.load(open(os.path.join(ROOT, w["plan"])))
        ahead = [p for p in plan.get("prep_schedule", []) if date.isoformat() in p.get("dates", [])]
        if ahead:
            print("\n".join(["🧑‍🍳 Prep day for next week's meals:"] + [f"• {p['task']}" for p in ahead]))
            return
    print("NOTHING")


if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("help", [])
    if cmd == "catalog":
        build_catalog()
    elif cmd == "candidates":
        candidates(dt.date.fromisoformat(args[0]) if args else next_monday())
    elif cmd == "weather":
        weather()
    elif cmd == "ingredients":
        ingredients(args)
    elif cmd == "render":
        render(args[0])
    elif cmd == "log":
        cat = catalog()
        def plan_lookup(date, meal):
            for w in reversed(history()):
                plan = json.load(open(os.path.join(ROOT, w["plan"])))
                if meal in ("breakfast", "lunch") and w["week_start"] <= date <= (dt.date.fromisoformat(w["week_start"]) + dt.timedelta(days=6)).isoformat():
                    return plan["breakfast_lunch"][meal]
                for d in plan["days"]:
                    if d["date"] == date and not d["dinner"].get("rest"):
                        return d["dinner"]["id"]
            return None
        if args[0] == "add":
            cooklog.add(json.loads(args[1]), plan_lookup, cat)
        elif args[0] == "seen":
            print("SEEN" if cooklog.seen(args[1]) else "NEW")
        elif args[0] == "sync":
            # args[1]: a JSON file holding the feedback page's documents (ArtifactData list output, or a list of bodies)
            if not os.path.exists(args[1]):  # an empty feedback collection writes no folder
                print("SYNCED 0 new feedback entries (no feedback saved yet)"); sys.exit(0)
            if os.path.isdir(args[1]):  # ArtifactData list with out_dir: one JSON body per document
                docs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(args[1], "**", "*.json"), recursive=True))]
            else:
                raw = json.load(open(args[1]))
                docs = raw if isinstance(raw, list) else raw.get("documents") or raw.get("docs") or raw.get("items") or []
            new = cooklog.page_entries(docs)
            for e in new:
                cooklog.add(e, plan_lookup, cat)
            print(f"SYNCED {len(new)} new feedback entr{'y' if len(new) == 1 else 'ies'}")
        elif args[0] == "xlsx":
            cooklog.build_xlsx(cat); print(cooklog.XLSX)
    elif cmd == "feedback-plan":
        # body for the Kitchen Log page's plan/current document: every planned day from 7 days ago through the newest plan
        cat = catalog()
        since = ((dt.date.fromisoformat(args[0]) if args else dt.date.today()) - dt.timedelta(days=7)).isoformat()
        assets = json.load(open(PDF_ASSETS)) if os.path.exists(PDF_ASSETS) else {}
        recipes = {}
        def item(rid):
            r = cat[rid]
            if rid not in recipes:
                recipes[rid] = {k: r.get(k) for k in ("title", "serves", "prep", "hands_on", "total", "adapted", "notes", "ahead", "url", "source")}
                recipes[rid]["ingredients"] = r["ingredients"]; recipes[rid]["steps"] = r.get("steps", [])
                recipes[rid]["videos"] = [{"title": v["title"], "channel": v.get("channel"), "url": v["url"], "length": v.get("length"), "why": v.get("why")}
                                          for v in (r.get("videos") or [])][:3]
                a = assets.get(rid)
                if a and r.get("pdf") and os.path.exists(r["pdf"]) and abs(a.get("mtime", 0) - os.path.getmtime(r["pdf"])) < 1:
                    recipes[rid]["pdf"] = "/_blob/" + a["asset"]
            return {"id": rid, "title": r["title"], "url": r["url"], "folder": r["folder"].replace("_", " "), "lesson": config.is_lesson(rid, cat)}
        days = {}
        for w in history():
            plan = json.load(open(os.path.join(ROOT, w["plan"])))
            bl = plan["breakfast_lunch"]
            for d in plan["days"]:
                if d["date"] < since:
                    continue
                day = {"date": d["date"], "breakfast": item(bl["breakfast"]), "lunch": item(bl["lunch"])}
                if d["dinner"].get("rest"):
                    day["rest"] = True
                    if d["dinner"].get("leftovers_of"):
                        day["leftovers"] = cat[d["dinner"]["leftovers_of"]]["title"]
                else:
                    day["dinner"] = item(d["dinner"]["id"])
                days[d["date"]] = day
        days = [days[k] for k in sorted(days)]
        print(json.dumps({"updated": dt.date.today().isoformat(), "days": days, "recipes": recipes}, ensure_ascii=False) if days else "NO_PLAN")
    elif cmd == "pdfs-needed":
        # recipe PDFs referenced by the Kitchen Log window that aren't uploaded yet (or changed since upload)
        cat = catalog(); assets = json.load(open(PDF_ASSETS)) if os.path.exists(PDF_ASSETS) else {}
        since = (dt.date.today() - dt.timedelta(days=7)).isoformat(); ids = set()
        for w in history():
            plan = json.load(open(os.path.join(ROOT, w["plan"])))
            if any(d["date"] >= since for d in plan["days"]):
                ids |= {d["dinner"]["id"] for d in plan["days"] if not d["dinner"].get("rest") and d["date"] >= since}
                ids |= {plan["breakfast_lunch"]["breakfast"], plan["breakfast_lunch"]["lunch"]}
        for rid in sorted(ids):
            if not cat[rid].get("pdf") or not os.path.exists(cat[rid]["pdf"]):
                continue
            a = assets.get(rid)
            if not a or abs(a.get("mtime", 0) - os.path.getmtime(cat[rid]["pdf"])) >= 1:
                print(rid, cat[rid]["pdf"], sep="\t")
    elif cmd == "pdf-asset":
        # record an uploaded PDF: planner.py pdf-asset RECIPE_ID BLOB_ID
        cat = catalog(); assets = json.load(open(PDF_ASSETS)) if os.path.exists(PDF_ASSETS) else {}
        blob = args[1].rsplit("/", 1)[-1]
        assets[args[0]] = {"asset": blob, "mtime": os.path.getmtime(cat[args[0]]["pdf"])}
        json.dump(assets, open(PDF_ASSETS, "w"), indent=1); print("recorded", args[0], blob)
    elif cmd == "order-list":
        # items for order N (1 = Sunday, 2 = midweek), minus items whose dishes were skipped/moved or are no longer planned
        plan = json.load(open(args[0])); order = int(args[1])
        lp = os.path.join(HERE, "cook_log.json")
        off = {(e["date"], e["id"]) for e in (json.load(open(lp)) if os.path.exists(lp) else [])
               if e.get("status") in ("skipped", "moved") and e.get("meal", "dinner") == "dinner"}
        planned = {d["dinner"]["id"] for d in plan["days"] if not d["dinner"].get("rest") and (d["date"], d["dinner"]["id"]) not in off}
        planned |= {plan["breakfast_lunch"]["breakfast"], plan["breakfast_lunch"]["lunch"]}
        for a in plan["groceries"]:
            for i in a["items"]:
                if i.get("order", 1) != order:
                    continue
                ids = set(re.findall(r"[A-Z]+-[\d.]+", i.get("for", "")))
                keep = not ids or ids & planned
                print(("BUY" if keep else "DROP") + f"\t{a['aisle']}\t{i['item']}\t{i['qty']}\t{i.get('for', '')}")
    elif cmd == "cart-text":
        # the "groceries are in the cart" text, written next to plan.json as cart_text.txt
        plan_path = args[0]; plan = json.load(open(plan_path)); order = int(args[1]) if len(args) > 1 else 1
        start = dt.date.fromisoformat(plan["week_start"])
        pre = "" if order == 1 else "2"
        two = any(i.get("order", 1) == 2 for a in plan.get("groceries", []) for i in a["items"])
        status = plan.get(f"cart{pre}_status") or "Cart status unknown."
        failed = status.lower().startswith("not filled")
        waiting = status.lower().startswith("waiting")
        label = {1: f"Order 1 ({O1})", 2: f"Order 2 ({O2})"}[order] if two else "Groceries"
        t = [(f"🛒 Couldn't fill {label}" if failed else f"🛒 {label} is on hold" if waiting else f"🛒 {label} is in your cart") + f" · week of {start:%b %-d}", "", status]
        details = (plan.get(f"cart{pre}_details") or "").strip()
        if details and not failed and not waiting:
            t += ["", details if len(details) <= 700 else details[:700].rsplit(" ", 1)[0] + "… (full details in the plan PDF)"]
        if plan.get("pantry_alerts") and order == 1:
            t += ["", "Pantry restock added: " + "; ".join(plan["pantry_alerts"])]
        if two and order == 1 and not failed:
            t += ["", f"Check out Order 1 (pick a {O1} slot) before {O2_FILL}. Then I'll fill Order 2 ({O2_SPAN} dinners) in the empty cart."]
        t += ["", f"Full grocery list: {display_path(os.path.join(PLANS, plan['week_start'], 'Meal_Plan_' + plan['week_start'] + '.pdf'))}"]
        out = os.path.join(os.path.dirname(os.path.abspath(plan_path)), f"cart_text{pre}.txt")
        open(out, "w").write("\n".join(t)); print(out)
    elif cmd == "spend":
        # planner.py spend add ORDER# YYYY-MM-DD AMOUNT   |   planner.py spend [DATE]  (that week's and last week's totals)
        if args and args[0] == "add":
            cooklog.add_order(args[1], args[2], args[3]); cooklog.build_xlsx(catalog())
            print(f"recorded order {args[1]} ({args[2]}): ${float(args[3].replace('$', '').replace(',', '')):.2f}")
        else:
            d = dt.date.fromisoformat(args[0]) if args else dt.date.today()
            weeks = cooklog.spending_by_week()
            for label, wk in (("this week", d - dt.timedelta(days=d.weekday())), ("last week", d - dt.timedelta(days=d.weekday() + 7))):
                v = weeks.get(wk, {"orders": 0, "total": 0})
                print(f"Groceries {label} (week of {wk:%b %-d}): ${v['total']:.2f} across {v['orders']} order(s)")
    elif cmd == "recap":
        # the 7 days before today (on a Friday: last Fri–Sun plus this Mon–Thu)
        end = dt.date.fromisoformat(args[0]) if args else dt.date.today()
        days = []
        for w in history():
            for d in json.load(open(os.path.join(ROOT, w["plan"])))["days"]:
                if (end - dt.timedelta(days=7)).isoformat() <= d["date"] < end.isoformat():
                    days.append(d)
        cooklog.recap(end, catalog(), sorted(days, key=lambda d: d["date"]))
    elif cmd == "tonight-text":
        tonight_text(dt.date.fromisoformat(args[0]) if args else dt.date.today())
    elif cmd == "tonight":
        tonight(dt.date.fromisoformat(args[0]) if args else dt.date.today())
    else:
        print(__doc__)
