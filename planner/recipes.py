"""Reads your recipe collection: one JSON file per recipe (or a JSON list of recipes per file) under recipes_dir.

Required fields: id, folder, section, title, serves, ingredients ([[group, [lines]]]), steps ([[title, text]]).
Optional: cuisine, difficulty, prep, cook, total, adapted (scaling note), ahead (make-ahead/storage),
nutrition (portion note), skills, why_short, url, source, pdf (path to your own PDF of the recipe),
hands_on (active minutes), notes (household and safety notes),
rating (the COOK's own 1–5 rating; never the published one), videos ([{title, url, length, why}] technique videos to watch first). See recipes/README.md for the full format and examples.
"""
import glob, json, os
import config

FIELDS = ("id", "folder", "section", "title", "cuisine", "difficulty", "prep", "cook", "total", "hands_on", "serves",
          "adapted", "ahead", "nutrition", "notes", "skills", "why_short", "url", "source", "rating")


def load():
    out = []
    for f in sorted(glob.glob(os.path.join(config.RECIPES, "**", "*.json"), recursive=True)):
        data = json.load(open(f))
        for r in (data if isinstance(data, list) else [data]):
            missing = [k for k in ("id", "folder", "section", "title", "serves", "ingredients", "steps") if k not in r]
            if missing:
                raise SystemExit(f"{f}: recipe {r.get('id', '?')} is missing {missing}")
            e = {k: r.get(k) for k in FIELDS}
            e["ingredients"] = [[g, list(items)] for g, items in r["ingredients"]]
            e["steps"] = [list(s) if isinstance(s, (list, tuple)) else ["", s] for s in r["steps"]]
            e["videos"] = [v for v in (r.get("videos") or []) if isinstance(v, dict) and v.get("url")]
            pdf = r.get("pdf")
            e["pdf"] = config.path(pdf) if pdf else None
            e["pdf_label"] = os.path.relpath(e["pdf"], os.path.dirname(config.RECIPES)) if pdf else ""
            e["_file"] = f
            out.append(e)
    ids = [r["id"] for r in out]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise SystemExit(f"Duplicate recipe ids: {sorted(dup)}")
    return out


def newest_mtime():
    files = glob.glob(os.path.join(config.RECIPES, "**", "*.json"), recursive=True)
    return max((os.path.getmtime(f) for f in files), default=0)
