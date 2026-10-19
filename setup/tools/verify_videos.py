"""Check every recipe video against YouTube's oEmbed endpoint (titles must match; links must be live).

  python3 setup/tools/verify_videos.py           # report problems
  python3 setup/tools/verify_videos.py --prune   # also remove dead links (rewrites those recipe files, 1-space JSON indent)
"""
import glob, json, os, re, subprocess, sys, unicodedata, urllib.parse

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KIT, "planner"))
import config  # noqa: E402


def norm(t):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", t or "")).strip().lower()


def check(v):
    url = v.get("url", "")
    if "youtube.com" not in url and "youtu.be" not in url:
        code = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-L", "-m", "20", url],
                              capture_output=True, text=True).stdout
        return ("ok", "") if code == "200" else ("dead", f"HTTP {code}")
    out = subprocess.run(["curl", "-s", "-m", "20", "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(url, safe="")],
                         capture_output=True, text=True).stdout
    try:
        d = json.loads(out)
    except Exception:
        return "dead", "not found on YouTube"
    if norm(d.get("title")) != norm(v.get("title")):
        return "title", f"YouTube title is {d.get('title')!r}"
    if v.get("channel") and norm(d.get("author_name")) != norm(v.get("channel")):
        return "channel", f"YouTube channel is {d.get('author_name')!r}"
    return "ok", ""


def main():
    prune = "--prune" in sys.argv
    total = bad = 0
    for f in sorted(glob.glob(os.path.join(config.RECIPES, "**", "*.json"), recursive=True)):
        data = json.load(open(f))
        recs = data if isinstance(data, list) else [data]
        changed = False
        for r in recs:
            keep = []
            for v in r.get("videos") or []:
                total += 1
                status, note = check(v)
                if status != "ok":
                    bad += 1
                    print(f"{status.upper():5} {r['id']}: {v.get('title', '')[:60]} {v.get('url', '')} {note}")
                if status == "dead" and prune:
                    changed = True
                    continue
                keep.append(v)
            if changed:
                r["videos"] = keep
        if changed:
            json.dump(data, open(f, "w"), indent=1, ensure_ascii=False)
    print(f"{total} video(s) checked, {bad} problem(s)" + (" (dead links removed)" if prune and bad else ""))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
