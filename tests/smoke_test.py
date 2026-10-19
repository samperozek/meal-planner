"""End-to-end smoke test on the sample recipes, in a throwaway data folder. No network, texts or carts.

  python3 tests/smoke_test.py
"""
import json, os, shutil, subprocess, sys, tempfile

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def run(*args, ok_codes=(0,)):
    r = subprocess.run([PY, *args], cwd=KIT, capture_output=True, text=True, env=ENV)
    if r.returncode not in ok_codes:
        print(r.stdout, r.stderr)
        raise SystemExit(f"FAILED: {' '.join(args)} (exit {r.returncode})")
    return r.stdout


tmp = tempfile.mkdtemp(prefix="meal-plan-smoke-")
cfg = json.load(open(os.path.join(KIT, "config.example.json")))
cfg["paths"] = {"data_dir": os.path.join(tmp, "data"), "recipes_dir": os.path.join(KIT, "examples", "recipes")}
cfg["kitchen_log"]["url"] = "https://example.com/kitchen-log"
json.dump(cfg, open(os.path.join(tmp, "config.json"), "w"))
ENV = {**os.environ, "MEAL_PLAN_CONFIG": os.path.join(tmp, "config.json")}

try:
    run("setup/tools/validate_recipes.py")
    assert "catalog.json: 13 recipes" in run("planner/planner.py", "catalog")
    out = run("planner/planner.py", "candidates", "2026-10-26")
    assert "CS-1.1" in out and "BREAKFAST" in out

    week = os.path.join(tmp, "data", "Meal_Plans", "2026-10-26")
    os.makedirs(week, exist_ok=True)
    plan = {
        "week_start": "2026-10-26", "summary": "Smoke-test week.", "alerts": ["Test alert"], "cart_pending": True,
        "days": [
            {"date": "2026-10-26", "dinner": {"id": "WK-01", "scale": 1}},
            {"date": "2026-10-27", "dinner": {"rest": True, "leftovers_of": "WK-01", "note": "Reheat"}},
            {"date": "2026-10-28", "dinner": {"id": "GL-01", "scale": 1}},
            {"date": "2026-10-29", "dinner": {"id": "WK-02", "scale": 1}},
            {"date": "2026-10-30", "dinner": {"rest": True, "note": "Takeout"}},
            {"date": "2026-10-31", "dinner": {"id": "WK-04", "scale": 0.67, "scale_note": "Make two thirds"}},
            {"date": "2026-11-01", "dinner": {"id": "CS-1.1", "scale": 1}}],
        "breakfast_lunch": {"breakfast": "BF-02", "lunch": "LU-02", "breakfast_batches": 2, "lunch_batches": 1.5},
        "prep_schedule": [{"when": "Sat night", "dates": ["2026-10-31"], "task": "Read tomorrow's lesson"}],
        "groceries": [{"aisle": "Produce", "items": [
            {"item": "Lemons", "qty": "2", "for": "WK-01", "order": 1},
            {"item": "Zucchini", "qty": "1", "for": "CS-1.1", "order": 2}]}],
    }
    path = os.path.join(week, "plan.json")
    json.dump(plan, open(path, "w"))
    run("planner/planner.py", "render", path)
    assert os.path.exists(os.path.join(week, "Meal_Plan_2026-10-26.pdf"))
    text = open(os.path.join(week, "text.txt")).read()
    assert "Leftovers" in text and "Order 2" in text

    assert "Tonight: Sheet-Pan Lemon Chicken" in run("planner/planner.py", "tonight-text", "2026-10-26")
    assert "Leftovers tonight" in run("planner/planner.py", "tonight-text", "2026-10-27")
    assert "Read tomorrow's lesson" in run("planner/planner.py", "tonight-text", "2026-10-31")
    assert "BUY" in run("planner/planner.py", "order-list", path, "2")
    run("planner/planner.py", "cart-text", path, "1")
    assert json.loads(run("planner/planner.py", "feedback-plan", "2026-10-26"))["days"]

    run("planner/pantry.py", "check", path)
    run("planner/pantry.py", "deduct", "2026-10-28")
    run("planner/planner.py", "log", "add", json.dumps({"date": "2026-10-26", "rating": 4, "change": "more lemon"}))
    run("planner/planner.py", "log", "xlsx")
    assert os.path.exists(os.path.join(tmp, "data", "Cook_Log.xlsx"))

    pdf_dir = os.path.join(tmp, "pdfs")
    shutil.copytree(os.path.join(KIT, "examples", "recipes"), pdf_dir)
    cfg["paths"]["recipes_dir"] = pdf_dir
    json.dump(cfg, open(os.path.join(tmp, "config.json"), "w"))
    assert "13 PDF(s)" in run("setup/tools/recipe_pdf.py")
    print("smoke test passed")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
