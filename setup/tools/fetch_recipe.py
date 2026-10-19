"""Read a published recipe page's structured data (schema.org Recipe JSON-LD): exact ingredients, steps,
times, yield, author and rating with vote count. Research agents use this before writing a recipe.

  python3 setup/tools/fetch_recipe.py https://www.example.com/some-recipe/

Prints a readable summary, or BLOCKED / NO_RECIPE_DATA so the agent can move on to another source quickly.
"""
import html, json, re, subprocess, sys

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"


def fetch(url):
    r = subprocess.run(["curl", "-sL", "-m", "25", "-A", UA, "-H", "Accept-Language: en-US,en;q=0.9",
                        "-w", "\n__STATUS__%{http_code}", url], capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n__STATUS__")
    return code.strip(), body


def find_recipe(obj):
    if isinstance(obj, list):
        for o in obj:
            found = find_recipe(o)
            if found:
                return found
    elif isinstance(obj, dict):
        t = obj.get("@type")
        if t == "Recipe" or (isinstance(t, list) and "Recipe" in t):
            return obj
        for key in ("@graph", "mainEntity", "itemListElement"):
            if key in obj:
                found = find_recipe(obj[key])
                if found:
                    return found
    return None


def text(x):
    if isinstance(x, list):
        return ", ".join(text(i) for i in x)
    if isinstance(x, dict):
        return x.get("name") or x.get("text") or ""
    return html.unescape(re.sub(r"<[^>]+>", "", str(x or ""))).strip()


def duration(iso):
    m = re.match(r"P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?", iso or "")
    if not m or not (m.group(1) or m.group(2)):
        return ""
    h, mi = int(m.group(1) or 0), int(m.group(2) or 0)
    return (f"{h} hr " if h else "") + (f"{mi} min" if mi else "").strip()


def steps(instr, depth=0):
    out = []
    for s in instr if isinstance(instr, list) else [instr]:
        if isinstance(s, dict) and s.get("@type") == "HowToSection":
            out.append(("  " * depth) + f"[{text(s.get('name'))}]")
            out += steps(s.get("itemListElement", []), depth + 1)
        else:
            t = text(s)
            if t:
                out.append(("  " * depth) + t)
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    url = sys.argv[1]
    code, body = fetch(url)
    if code != "200" or len(body) < 500:
        print(f"BLOCKED (HTTP {code}): try another source, or WebFetch if you must (it may paraphrase quantities)")
        sys.exit(1)
    recipe, nodes = None, {}
    for block in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', body, re.S | re.I):
        try:
            data = json.loads(block.strip())
        except Exception:
            continue
        for n in (data.get("@graph", []) if isinstance(data, dict) else data if isinstance(data, list) else []):
            if isinstance(n, dict) and n.get("@id"):
                nodes[n["@id"]] = n
        recipe = recipe or find_recipe(data)
    resolve = lambda x: [resolve(i) for i in x] if isinstance(x, list) else (nodes.get(x["@id"], x) if isinstance(x, dict) and set(x) == {"@id"} else x)
    if not recipe:
        print("NO_RECIPE_DATA: the page has no structured recipe data; read it with WebFetch and copy quantities carefully")
        sys.exit(1)
    rating = recipe.get("aggregateRating") or {}
    print(f"TITLE: {text(recipe.get('name'))}")
    print(f"AUTHOR: {text(resolve(recipe.get('author')))}")
    print(f"PUBLISHER: {text(resolve(recipe.get('publisher')))}")
    print(f"URL: {url}")
    if rating:
        print(f"RATING: {rating.get('ratingValue')}/5 ({rating.get('ratingCount') or rating.get('reviewCount')} ratings)")
    print(f"YIELD: {text(recipe.get('recipeYield'))}")
    print(f"TIMES: prep {duration(recipe.get('prepTime'))} · cook {duration(recipe.get('cookTime'))} · total {duration(recipe.get('totalTime'))}")
    print(f"CUISINE: {text(recipe.get('recipeCuisine'))}")
    if recipe.get("nutrition"):
        n = recipe["nutrition"]
        print("NUTRITION (per serving): " + ", ".join(f"{k.replace('Content', '')} {v}" for k, v in n.items() if k not in ("@type",) and v))
    print("\nINGREDIENTS (exactly as published):")
    for i in recipe.get("recipeIngredient", []):
        print("  - " + text(i))
    print("\nMETHOD (source wording; paraphrase it, never copy):")
    for n, s in enumerate(steps(recipe.get("recipeInstructions", [])), 1):
        print(f"  {n}. {s}")


if __name__ == "__main__":
    main()
