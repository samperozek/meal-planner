"""Cook log: feedback on what was cooked, synced from your Kitchen Log page (or given in a Claude session).

cook_log.json is the source of truth. Cook_Log.xlsx (in data_dir) is rebuilt from it after every change,
for browsing; edits made in the spreadsheet are overwritten.

Commands (via planner.py):
  planner.py log add '<json>'     add one entry (see ENTRY below); prints the stored entry
  planner.py log seen MSG_ID      exit 0 if this Gmail message id was already logged
  planner.py log xlsx             rebuild Cook_Log.xlsx
  planner.py recap [DATE]         the 7 days before DATE: planned dinners vs. log (for the Friday email)

ENTRY fields (only "date" is required; for a dinner the recipe id is filled from that day's plan):
  {"date": "2026-10-29", "meal": "dinner|breakfast|lunch", "id": "HER-05", "status": "cooked|skipped|moved",
   "rating": 4, "family": "kids loved it", "worked": "...", "change": "simmer 10 min longer",
   "would_repeat": "yes|tweak|no", "source_msg": "<gmail message id>", "raw": "<reply text, quotes stripped>"}
"""
import datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(config.STATE, "cook_log.json")
XLSX = os.path.join(config.DATA, "Cook_Log.xlsx")


def orders_path():
    return os.path.join(os.path.dirname(LOG), "orders.json")


def load_orders():
    p = orders_path()
    return json.load(open(p)) if os.path.exists(p) else []


def add_order(order, date, amount, store="Whole Foods"):
    """Record a confirmed grocery order. date = its delivery date; amount = the payment authorization in the confirmation email."""
    orders = [o for o in load_orders() if o["order"] != order]
    orders.append({"order": order, "date": date, "amount": round(float(str(amount).replace("$", "").replace(",", "")), 2), "store": store})
    orders.sort(key=lambda o: o["date"])
    json.dump(orders, open(orders_path(), "w"), indent=1)
    return orders


def week_of(d):
    """The Mon–Sun plan week an order is for: a Sunday delivery stocks the week that starts the next day."""
    d = dt.date.fromisoformat(d) + dt.timedelta(days=1)
    return d - dt.timedelta(days=d.weekday())


def spending_by_week():
    weeks = defaultdict(lambda: {"orders": 0, "total": 0.0})
    for o in load_orders():
        w = weeks[week_of(o["date"])]
        w["orders"] += 1; w["total"] = round(w["total"] + o["amount"], 2)
    return dict(sorted(weeks.items()))


def load():
    return json.load(open(LOG)) if os.path.exists(LOG) else []


def save(entries):
    entries.sort(key=lambda e: (e["date"], e.get("meal", "dinner")))
    json.dump(entries, open(LOG, "w"), indent=1, ensure_ascii=False)


def tier(avg, n, last_repeat):
    if last_repeat == "no" or (avg is not None and avg <= 2):
        return "Drop"
    if avg is None:
        return "Unrated"
    if avg >= 4.5 and n >= 2:
        return "Favorite"
    if avg >= 4:
        return "Keeper"
    return "Tweak"


def stats(cat):
    """Per-title stats (titles, not ids, because some dishes are cross-listed under several ids)."""
    by = defaultdict(list)
    for e in load():
        if e.get("id") in cat:
            by[cat[e["id"]]["title"]].append(e)
    out = {}
    for title, es in by.items():
        cooked = [e for e in es if e.get("status", "cooked") == "cooked"]
        rated = [e["rating"] for e in cooked if isinstance(e.get("rating"), (int, float))]
        avg = round(sum(rated) / len(rated), 2) if rated else None
        last = cooked[-1] if cooked else None
        change = next((e["change"] for e in reversed(cooked) if e.get("change")), None)
        rep = next((e["would_repeat"] for e in reversed(cooked) if e.get("would_repeat")), None)
        trend = None
        if len(rated) >= 2:
            trend = "▲" if rated[-1] > rated[-2] else "▼" if rated[-1] < rated[-2] else "="
        out[title] = {"n": len(cooked), "skips": len(es) - len(cooked), "avg": avg, "last_rating": rated[-1] if rated else None,
                      "last_date": last["date"] if last else None, "last_change": change, "last_change_date":
                      next((e["date"] for e in reversed(cooked) if e.get("change")), None),
                      "would_repeat": rep, "trend": trend, "tier": tier(avg, len(cooked), rep)}
    return out


def add(entry, plan_lookup, cat):
    entries = load()
    if entry.get("source_msg") and any(e.get("source_msg") == entry["source_msg"] and e.get("meal", "dinner") == entry.get("meal", "dinner")
                                       for e in entries):
        print("ALREADY_LOGGED"); return
    entry.setdefault("meal", "dinner"); entry.setdefault("status", "cooked")
    if not entry.get("id"):
        entry["id"] = plan_lookup(entry["date"], entry["meal"])
    if entry.get("id") not in cat:
        raise SystemExit(f"Unknown recipe id {entry.get('id')!r} for {entry['date']} {entry['meal']}")
    if entry.get("rating") is not None:
        entry["rating"] = max(1, min(5, round(float(entry["rating"]) * 2) / 2))
    entry["title"] = cat[entry["id"]]["title"]
    entry["logged_at"] = dt.datetime.now().isoformat(timespec="minutes")
    # a later reply about the same meal on the same day replaces the earlier one
    entries = [e for e in entries if not (e["date"] == entry["date"] and e.get("meal", "dinner") == entry["meal"] and e.get("id") == entry["id"])]
    entries.append(entry); save(entries)
    build_xlsx(cat)
    print(json.dumps(entry, indent=1, ensure_ascii=False))


def seen(msg_id):
    return any(e.get("source_msg") == msg_id for e in load())


# ------------------------------------------------------------------ spreadsheet
def build_xlsx(cat):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.formatting.rule import CellIsRule
    from openpyxl.worksheet.table import Table, TableStyleInfo
    WINE, CREAM = "7A2331", "F6F1E9"
    hdr_font, hdr_fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor=WINE)
    TIER_FILL = {"Favorite": "D9EAD3", "Keeper": "EEF2EA", "Tweak": "FFF2CC", "Drop": "F4CCCC", "Unrated": "FFFFFF"}
    entries = load(); st = stats(cat)
    wb = Workbook()

    def sheet(ws, headers, rows, widths, name):
        ws.append(headers)
        for r in rows:
            ws.append(r)
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[ws.cell(1, i).column_letter].width = w
        for c in ws[1]:
            c.font, c.fill, c.alignment = hdr_font, hdr_fill, Alignment(vertical="center", wrap_text=True)
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(vertical="top", wrap_text=True)
        ws.freeze_panes = "B2"
        if rows:
            t = Table(displayName=name, ref=ws.dimensions)
            t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
            ws.add_table(t)

    # 1. Rankings: every dish cooked at least once, best first
    ws = wb.active; ws.title = "Rankings"
    ranked = []
    for title, s in st.items():
        rid = next(e["id"] for e in entries if e.get("title") == title)
        r = cat[rid]
        ranked.append((s, r, title))
    order = {"Favorite": 0, "Keeper": 1, "Tweak": 2, "Unrated": 3, "Drop": 4}
    ranked.sort(key=lambda x: (order[x[0]["tier"]], -(x[0]["avg"] or 0), -x[0]["n"]))
    meal = lambda r: {"Breakfast": "Breakfast", "Lunches": "Lunch"}.get(r["folder"], "Dinner")
    rows = [[i + 1, title, meal(r), s["tier"], s["avg"], s["n"], s["last_rating"], s["trend"] or "", s["last_date"], s["skips"],
             s["would_repeat"] or "", s["last_change"] or "", r["folder"].replace("_", " "), r["cuisine"], r["id"]]
            for i, (s, r, title) in enumerate(ranked)]
    sheet(ws, ["Rank", "Dish", "Meal", "Tier", "Avg ★", "Times made", "Last ★", "Trend", "Last made", "Skipped", "Make again?",
               "Change next time (latest)", "Folder", "Cuisine", "ID"], rows,
          [6, 38, 10, 10, 7, 8, 7, 7, 11, 8, 10, 48, 18, 18, 10], "Rankings")
    for row in ws.iter_rows(min_row=2):
        row[3].fill = PatternFill("solid", fgColor=TIER_FILL.get(row[3].value, "FFFFFF"))
        row[4].number_format = "0.0"

    # 2. Log: one row per reply, newest first
    ws = wb.create_sheet("Log")
    rows = []
    for e in sorted(entries, key=lambda e: e["date"], reverse=True):
        d = dt.date.fromisoformat(e["date"])
        r = cat.get(e["id"], {})
        rows.append([d, d.strftime("%a"), e.get("meal", "dinner").title(), e.get("title"), e.get("status", "cooked").title(),
                     e.get("rating"), e.get("family") or "", e.get("worked") or "", e.get("change") or "",
                     (e.get("would_repeat") or "").title(), r.get("folder", "").replace("_", " "), e["id"], e.get("raw") or ""])
    sheet(ws, ["Date", "Day", "Meal", "Dish", "Status", "★ (1–5)", "Family reaction", "What worked", "Change next time",
               "Make again?", "Folder", "ID", "Your reply"], rows,
          [11, 5, 9, 36, 9, 8, 24, 32, 36, 10, 16, 9, 50], "Log")
    for row in ws.iter_rows(min_row=2):
        row[0].number_format = "mmm d, yyyy"
    if rows:
        ws.conditional_formatting.add(f"F2:F{len(rows) + 1}", CellIsRule(operator="greaterThanOrEqual", formula=["4"], fill=PatternFill("solid", fgColor="D9EAD3")))
        ws.conditional_formatting.add(f"F2:F{len(rows) + 1}", CellIsRule(operator="lessThanOrEqual", formula=["2"], fill=PatternFill("solid", fgColor="F4CCCC")))

    # 3. Lesson progress (optional course in config recipes.lesson_folder)
    ws = wb.create_sheet(config.LESSON_LABEL[:31])
    cs_log = defaultdict(list)
    for e in entries:
        if config.is_lesson(e["id"], cat):
            cs_log[e["id"]].append(e)
    def cs_key(i):
        import re
        return [int(n) for n in re.findall(r"\d+", i)] or [0]
    rows = []
    for rid in sorted((i for i in cat if config.is_lesson(i, cat)), key=cs_key):
        es = cs_log.get(rid, [])
        cooked = [e for e in es if e.get("status", "cooked") == "cooked"]
        last = cooked[-1] if cooked else (es[-1] if es else None)
        rows.append([rid, cat[rid]["title"], (cat[rid].get("syllabus") or {}).get("module", ""),
                     "Done" if cooked else ("Skipped" if es else ""), dt.date.fromisoformat(last["date"]) if last else None,
                     last.get("rating") if last else None, (last.get("change") or "") if last else ""])
    sheet(ws, ["Lesson", "Dish", "Module", "Status", "Date", "★", "Notes for next time"], rows, [8, 40, 34, 9, 12, 5, 50], "Lessons")
    for row in ws.iter_rows(min_row=2):
        row[4].number_format = "mmm d, yyyy"
        if row[3].value == "Done":
            row[3].fill = PatternFill("solid", fgColor="D9EAD3")

    # 4. How it works
    ws = wb.create_sheet("How it works")
    for line in ["Cook Log: rebuilt automatically from your ratings. Edits made here are overwritten.",
                 "",
                 "To rate a meal: tap the link at the bottom of any 4 PM text (your Kitchen Log page), pick stars and quick notes, then tap Save.",
                 "Ratings reach this sheet at the next 4 PM text or Friday plan. Choose 'Skipped' if you didn't make it.",
                 "To fix an entry, change it on the page and save again; the newest version replaces the older one.",
                 "",
                 "Tiers: Favorite = avg ≥4.5 over 2+ times · Keeper = avg ≥4 · Tweak = below 4 · Drop = avg ≤2 or 'wouldn't make again'.",
                 "The planner brings Favorites back more often, skips Drops, and puts your 'change next time' note in the 4 PM text",
                 "the next time a dish is scheduled. Lessons count as done once logged as cooked; skipped lessons are rescheduled.",
                 "",
                 "Pantry tab: estimated levels of staples. Each day, planned meals are subtracted unless you marked them Skipped.",
                 "Friday's plan adds anything running low to the Whole Foods cart and tells you in the plan text.",
                 "'Starting guess' means the level hasn't been confirmed. Tell Claude, e.g. 'olive oil is full' or 'out of cumin', to correct it."]:
        ws.append([line])
    ws.column_dimensions["A"].width = 120
    ws["A1"].font = Font(bold=True, size=13, color=WINE)

    # 5. Spending (confirmed grocery orders)
    orders = load_orders()
    if orders:
        ws = wb.create_sheet("Spending")
        weeks = spending_by_week()
        rows = [[w, v["orders"], v["total"]] for w, v in weeks.items()]
        sheet(ws, ["Week of (Mon)", "Orders", "Total ($)"], rows, [14, 9, 11], "Spending")
        for row in ws.iter_rows(min_row=2):
            row[0].number_format = "mmm d, yyyy"; row[2].number_format = "$#,##0.00"
        ws.append([]); ws.append(["Order", "Date", "Amount ($)", "Store"])
        for o in orders:
            ws.append([o["order"], o["date"], o["amount"], o.get("store", "")])

    # 6. Pantry levels (estimated)
    try:
        import pantry
        pantry.sheet(wb)
    except Exception as e:  # never let the pantry tab break the cook log
        print("NOTE: pantry tab skipped:", e)

    try:
        wb.save(XLSX)
    except PermissionError:
        print("NOTE: Cook_Log.xlsx is locked (open in Excel?); it will be rebuilt next time.")


def recap(end, cat, days):
    """Compare the planned dinners in `days` (the 7 days before `end`) with what was logged."""
    if not days:
        print("NO_PLANNED_DAYS"); return
    entries = {(e["date"], e.get("meal", "dinner")): e for e in load()}
    print(f"RECAP {days[0]['date']} → {days[-1]['date']}")
    missing = []
    for d in days:
        din = d["dinner"]
        if din.get("rest"):
            continue
        e = entries.get((d["date"], "dinner"))
        title = cat[din["id"]]["title"]
        if e:
            print(f'  {d["date"]} {title}: {e.get("status")} {("★" + str(e["rating"])) if e.get("rating") else ""} {e.get("change") or ""}')
        else:
            missing.append(f'{d["date"]} {title}')
    lo, hi = days[0]["date"], days[-1]["date"]
    for k in ("breakfast", "lunch"):
        es = [e for (dd, m), e in entries.items() if m == k and lo <= dd <= hi]
        print(f"  {k}: " + ("; ".join(f'{e.get("title")} ★{e.get("rating")} {e.get("change") or ""}' for e in es) if es else "no feedback"))
    if missing:
        print("  NOT LOGGED (assume cooked unless told otherwise):", "; ".join(missing))


# ------------------------------------------------------------------ feedback page sync
FAMILY = {"Kids loved it", "Kids weren't into it"}
REPEAT = {"Make again": "yes", "Wouldn't make again": "no"}
WORKED = {"Great leftovers", "Kept well", "Kept me full"}


def page_entries(docs):
    """Turn feedback-page documents into log entries; skips versions already logged."""
    logged = {e.get("source_msg") for e in load()}
    out = []
    for d in docs:
        d = d.get("data", d) if isinstance(d, dict) else d
        if not isinstance(d, dict) or not d.get("date") or not d.get("updated_at"):
            continue
        src = f'page:{d["date"]}_{d.get("meal", "dinner")}:{d["updated_at"]}'
        if src in logged:
            continue
        chips = [c for c in (d.get("chips") or []) if isinstance(c, str)]
        note = (d.get("note") or "").strip()[:500]
        cooked = d.get("status", "cooked") == "cooked"
        changes = [c for c in chips if c not in FAMILY and c not in REPEAT and c not in WORKED]
        e = {"date": d["date"], "meal": d.get("meal", "dinner"), "status": "cooked" if cooked else "skipped",
             "source_msg": src, "raw": " · ".join(filter(None, [", ".join(chips), note]))}
        if d.get("id"):
            e["id"] = d["id"]
        if cooked and isinstance(d.get("rating"), (int, float)):
            e["rating"] = d["rating"]
        if cooked:
            fam = [c for c in chips if c in FAMILY]
            if fam: e["family"] = "; ".join(fam)
            wk = [c for c in chips if c in WORKED]
            if wk: e["worked"] = "; ".join(wk)
            ch = "; ".join(filter(None, [note] + [c.lower() for c in changes]))
            if ch: e["change"] = ch
            rep = next((REPEAT[c] for c in chips if c in REPEAT), None)
            if rep: e["would_repeat"] = rep
            elif changes: e["would_repeat"] = "tweak"
        out.append(e)
    return out
