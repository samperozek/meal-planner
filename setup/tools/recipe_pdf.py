"""Render a clean, phone- and print-friendly PDF for each recipe, saved next to its JSON file.

  python3 setup/tools/recipe_pdf.py              # every recipe
  python3 setup/tools/recipe_pdf.py WK-01 CS-1.1 # just these
  add --no-link to leave the recipe files untouched (otherwise each gets a "pdf" path for the Kitchen Log)
"""
import glob, json, os, sys

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KIT, "planner"))
import config  # noqa: E402
from pdfstyle import S, W, WINE, CREAM, RULE, esc, boxed  # noqa: E402
from reportlab.lib.pagesizes import letter  # noqa: E402
from reportlab.lib.units import inch  # noqa: E402
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether  # noqa: E402


def P(t, st="body"):
    return Paragraph(t, S[st])


def build(r, path):
    flow = [P(esc(f"{r['folder'].replace('_', ' ')} · {r.get('section', '')}").upper(), "kicker"), P(esc(r["title"]), "title")]
    if r.get("why_short"):
        flow.append(P(esc(r["why_short"]), "native"))
    facts = [[P(f"<b>{k}</b>", "small") for k in ("Serves", "Hands-on", "Cook", "Total", "Level")],
             [P(esc(str(r.get(k) or "—")), "body") for k in ("serves", "hands_on" if r.get("hands_on") else "prep", "cook", "total", "difficulty")]]
    t = Table(facts, colWidths=[W / 5] * 5)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CREAM), ("LINEBELOW", (0, 0), (-1, 0), 0.4, RULE),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    flow += [t, Spacer(1, 6)]
    if r.get("adapted"):
        flow += [boxed([P("<b>Scaling</b>", "boxh"), P(esc(r["adapted"]), "box")]), Spacer(1, 6)]
    if r.get("notes"):
        notes = r["notes"] if isinstance(r["notes"], list) else [r["notes"]]
        flow += [boxed([P("<b>For your household</b>", "boxh")] + [P("• " + esc(n), "box") for n in notes]), Spacer(1, 6)]
    if r.get("videos"):
        flow.append(P("Watch first", "h2"))
        for v in r["videos"]:
            line = (f'<link href="{v["url"]}" color="#7A2331"><u>{esc(v["title"])}</u></link>' + (f" · {esc(v['channel'])}" if v.get("channel") else "")
                    + (f" · {esc(v['length'])}" if v.get("length") else ""))
            flow.append(P("• " + line + (f"<br/><font size='8'>{esc(v['why'])}</font>" if v.get("why") else ""), "item"))
    flow.append(P("Ingredients", "h2"))
    for group, items in r["ingredients"]:
        block = ([P(esc(group), "h3")] if group and len(r["ingredients"]) > 1 else []) + [P("• " + esc(i), "item") for i in items]
        flow.append(KeepTogether(block))
    flow.append(P("Method", "h2"))
    for n, (title, text) in enumerate(r["steps"], 1):
        flow.append(P(f"<font color='#7A2331'><b>{n}.</b></font> " + (f"<b>{esc(title)}.</b> " if title else "") + esc(text), "body"))
    for key, label in (("technique", "Why it works"), ("mistakes", "Common mistakes"), ("learn", "What you'll learn")):
        val = r.get(key)
        if val:
            flow.append(P(label, "h2"))
            for item in val:
                flow.append(P((f"<b>{esc(item[0])}</b> {esc(item[1])}" if isinstance(item, (list, tuple)) else "• " + esc(item)), "item"))
    for key, label in (("ahead", "Make ahead and storage"), ("nutrition", "Nutrition")):
        if r.get(key):
            flow += [P(label, "h2"), P(esc(r[key]), "body")]
    src = esc(r.get("source") or "")
    if r.get("url"):
        src = f'<link href="{r["url"]}" color="#7A2331"><u>{src or r["url"]}</u></link>'
    for a in r.get("also") or []:
        t = esc(f"{a.get('title', '')} ({a.get('source', '')})")
        src += "; also " + (f'<link href="{a["url"]}" color="#7A2331"><u>{t}</u></link>' if a.get("url") else t)
    if src:
        flow += [Spacer(1, 8), P("Source: " + src + ". Ingredients as published; method paraphrased.", "small")]
    SimpleDocTemplate(path, pagesize=letter, leftMargin=0.65 * inch, rightMargin=0.65 * inch, topMargin=0.6 * inch,
                      bottomMargin=0.6 * inch, title=r["title"]).build(flow)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    link = "--no-link" not in sys.argv
    n = 0
    for f in sorted(glob.glob(os.path.join(config.RECIPES, "**", "*.json"), recursive=True)):
        data = json.load(open(f))
        recs = data if isinstance(data, list) else [data]
        changed = False
        for r in recs:
            if not isinstance(r, dict) or "ingredients" not in r or (args and r.get("id") not in args):
                continue
            pdf = os.path.join(os.path.dirname(f), f"{r['id']}.pdf")
            build(r, pdf); n += 1
            if link:
                rel = os.path.relpath(pdf, os.path.dirname(config.CONFIG_PATH))
                if r.get("pdf") != rel:
                    r["pdf"] = rel; changed = True
        if changed:
            json.dump(data, open(f, "w"), indent=1, ensure_ascii=False)
    print(f"{n} PDF(s) written next to their recipe files")


if __name__ == "__main__":
    main()
