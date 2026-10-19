"""Find candidate technique videos on YouTube (title, channel, length, URL), for the video-research agents.

  python3 setup/tools/find_videos.py "jacques pepin omelette technique"
  python3 setup/tools/find_videos.py --page https://www.example.com/recipe/   # videos embedded on a recipe page

Candidates still have to pass verify_videos.py (oEmbed) before they go in a recipe.
"""
import json, re, subprocess, sys, urllib.parse

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"


def get(url):
    return subprocess.run(["curl", "-sL", "-m", "25", "-A", UA, "-H", "Accept-Language: en-US,en;q=0.9", url],
                          capture_output=True, text=True).stdout


def oembed(vid):
    try:
        d = json.loads(get("https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v=" + vid))
        return d.get("title", ""), d.get("author_name", "")
    except Exception:
        return None, None


def length(vid):
    m = re.search(r'"lengthSeconds":"(\d+)"', get("https://www.youtube.com/watch?v=" + vid))
    if not m:
        return ""
    s = int(m.group(1))
    return "under 1 min" if s < 60 else f"{round(s / 60)} min"


def search(q, limit=10):
    html = get("https://www.youtube.com/results?search_query=" + urllib.parse.quote(q))
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    if not m:
        print("NO_RESULTS: YouTube didn't return search data; try different words or --page on the recipe page"); return
    out, seen = [], set()

    def walk(o):
        if isinstance(o, dict):
            if "videoRenderer" in o:
                v = o["videoRenderer"]
                vid = v.get("videoId")
                if vid and vid not in seen:
                    seen.add(vid)
                    out.append((vid, "".join(r.get("text", "") for r in v.get("title", {}).get("runs", [])),
                                "".join(r.get("text", "") for r in v.get("ownerText", {}).get("runs", [])),
                                v.get("lengthText", {}).get("simpleText", "")))
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(json.loads(m.group(1)))
    for vid, title, ch, ln in out[:limit]:
        print(f"{ln:>8}  {ch[:30]:30}  {title[:80]}\n          https://www.youtube.com/watch?v={vid}")


def page(url):
    ids = []
    for vid in re.findall(r"(?:youtube(?:-nocookie)?\.com/(?:embed/|watch\?v=)|youtu\.be/)([A-Za-z0-9_-]{11})", get(url)):
        if vid not in ids:
            ids.append(vid)
    if not ids:
        print("NO_EMBEDDED_VIDEOS"); return
    for vid in ids:
        title, ch = oembed(vid)
        if title is None:
            continue
        print(f"{length(vid):>11}  {ch[:30]:30}  {title[:80]}\n             https://www.youtube.com/watch?v={vid}")
    print("Check each one is about this dish and comes from the recipe author's own channel (pages also embed promos and ads).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    if sys.argv[1] == "--page":
        page(sys.argv[2])
    else:
        search(" ".join(sys.argv[1:]))
