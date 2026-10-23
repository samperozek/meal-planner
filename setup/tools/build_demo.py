"""Build a shareable demo of the Kitchen Log page: a week's plan and recipes embedded in the page, no database.
Anyone can open it, browse recipes and try the rating form; ratings stay in their own browser.

  python3 setup/tools/build_demo.py [OUTPUT.html]     # default: <data_dir>/kitchen-log-demo.html

It uses your newest plan (planner.py feedback-plan). Publish the file as an Artifact and share its link.
Only share demos built from recipes you're free to share (e.g. the sample recipes); your own collection stays private.
"""
import json, os, subprocess, sys

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KIT, "planner"))
import config  # noqa: E402


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(config.DATA, "kitchen-log-demo.html")
    r = subprocess.run([sys.executable, os.path.join(KIT, "planner", "planner.py"), "feedback-plan"], capture_output=True, text=True)
    if r.returncode != 0 or r.stdout.strip() == "NO_PLAN":
        raise SystemExit("No plan to show yet: render a week first (planner.py render <plan.json>).")
    data = json.loads(r.stdout)
    for rec in data.get("recipes", {}).values():
        rec.pop("pdf", None)                     # private asset links don't work outside your own page
    page = open(os.path.join(KIT, "kitchen-log", "index.html")).read()
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = page.replace("<script>", f"<script>window.KITCHEN_DEMO = {blob};</script>\n<script>", 1)
    page = page.replace("<title>Kitchen Log</title>", "<title>Kitchen Log Demo</title>", 1)
    open(out, "w").write(page)
    print(f"Demo written to {out} ({len(data['days'])} days, {len(data['recipes'])} recipes)")


if __name__ == "__main__":
    main()
