# Recipe-sourcing brief (research agents: read fully before starting)

You're adding recipes to one cook's private collection. Your task message gives you their **profile** (`my-recipes/PROFILE.md`) and your **batch**: recipe ids, folder, section, dish names, the folder's criteria and the target number of servings. Follow the profile: allergies are absolute, dislikes are avoided, health rules are honored, and the folder's time and difficulty limits are respected. Run every command from the kit folder.

## The non-negotiable rule: established, published recipes only
Every recipe must be a specific, existing, well-regarded published recipe. **Never invent one.** Prefer notable chefs and authorities for the cuisine, test kitchens, and heavily tested, highly rated sites. Weigh the rating **and** the number of votes (4.9 from 300 beats 5.0 from 6).

If the dish you were given barely exists as a published recipe in that form (e.g. "sheet-pan enchiladas"), or no strong version is readable, choose the closest established dish that fits the folder and explain the swap in your report.

## Reading pages: use the tool first
```
python3 setup/tools/fetch_recipe.py <url>
```
It reads the page's built-in recipe data and prints the **exact** ingredients, yield, times, author and rating with vote count. If it prints `BLOCKED`, move on to another source. Fall back to WebFetch only for pages without recipe data, and copy quantities carefully, because summarized pages can drop or merge them.

**Sites that usually work:** Once Upon a Chef, RecipeTin Eats, Swasthi's Recipes (indianhealthyrecipes.com), Piping Pot Curry, Ministry of Curry, Cook with Manali, Skinnytaste, Love and Lemons, Minimalist Baker, Pinch of Yum, Downshiftology, Well Plated, The Woks of Life, Just One Cookbook, Hot Thai Kitchen. Food Network works through WebFetch only.

**Sites that usually block automated reading (skip them):** Serious Eats, Bon Appétit, Epicurious, Simply Recipes, BBC Good Food, Food & Wine, Food52, Budget Bytes, Cookie and Kate, The Mediterranean Dish, Half Baked Harvest, Two Peas and Their Pod, A Couple Cooks, Feel Good Foodie, Gimme Some Oven, Ambitious Kitchen, Rachel Cooks, Rainbow Plant Life, Feasting at Home, Eating Bird Food. Sites change, so trust what the tool tells you.

## Writing each recipe
**Ingredients**
- Copy names and quantities exactly as published, and never guess a quantity.
- You may make only small rewordings that put the amount first without changing it ("Juice of 1 lime" → "1 lime, juiced"), or add the accepted endings to unquantified lines: "…, to taste", "…, for serving", "…, for garnish", "…, as needed", "…, for the pan", "…, for drizzling", "a pinch of …". The validator accepts these.
- **Alternatives and extras** from the source's notes go in their own group whose name starts with **"Optional:"** or **"Alternative:"** (e.g. "Alternative: dried chickpeas instead of canned"). The planner doesn't buy or count those groups unless it chooses them.
- **Allergens:** if the source offers a variation using one of the cook's allergens (e.g. a cashew cream), leave it out entirely and mention it in your report. If an ingredient is a packaged product that might contain an allergen (spice blends, soy chorizo), add a label-check line to `notes`.
- Brand names: use the generic ingredient, with the brand in parentheses only if the source depends on it.

**Method**
- Write it in your own words. Keep every time, temperature, heat level and doneness cue, never copy the source's sentences, and don't add steps.
- If the source gives several methods (stovetop, Instant Pot, plain pot), make the one that fits the cook's equipment the main steps, and summarize the others in one `notes` line.

**Companions:** if a sauce or side comes from another source, merge it in as its own ingredient group plus steps, and add that source to `also`. If the companion makes something already in the ingredient list (e.g. hard-boiled eggs), don't list that ingredient twice.

**Fields with rules**
- `serves`: the **published** yield ("4 to 6"). Scaling to the household goes in `adapted` ("Serves 2 to 3 as published; double it for 4."); never rescale silently.
- `hands_on`: active minutes (chopping, stirring, assembling), from the source if it says, otherwise your honest estimate marked "(est.)". The weeknight cap is checked against this.
- `notes`: anything for this household that isn't scaling: toddler-mild options, choking cautions, allergen label checks, altitude adjustments, other methods. Use a list of short lines.
- `ahead`: the source's make-ahead and storage guidance. If it gives none, write: "The source gives no storage guidance. General guideline (not from the source): …"
- `nutrition`: only what the source states, as "Per source: …" on the source's own serving basis. For protein-target folders, add the portion that reaches the target ("Eat 1½ servings = 33 g protein").
- `source`: "Publisher (Author) · 4.9/5 (312 ratings)". **Never set `rating`**: that field is the cook's own score.
- `title`: descriptive and close to the source's title, using "and", not "&".

**High-protein folders:** look for recipes that reach the target in at most about 2 servings. If none that are well rated and readable get there, choose the best one and state the portion honestly, even if it's an odd number like 1⅓ servings. Mention any trade-off in your report.

## Output: one JSON file per recipe
Write `my-recipes/<Folder>/<id>.json` (UTF-8, with real characters like é, ½ and °F):

```json
{
  "id": "WK-05",
  "folder": "Weeknight",
  "section": "Skillet",
  "title": "Pan-Seared Chicken with Lemon Pan Sauce",
  "cuisine": "French technique",
  "difficulty": "Everyday",
  "prep": "15 min", "cook": "20 min", "total": "35 min", "hands_on": "15 min",
  "serves": "4",
  "skills": ["Searing", "Pan sauce"],
  "why_short": "One sentence (max 25 words): why this dish and this source.",
  "source": "Publisher (Author) · 4.8/5 (312 ratings)",
  "url": "https://…",
  "also": [{"title": "Lemon Pan Sauce", "source": "Publisher (Author)", "url": "https://…"}],
  "adapted": "",
  "notes": ["Mild for the toddler: hold back the chili flakes."],
  "ingredients": [["Chicken", ["4 boneless, skinless chicken breasts (6 to 8 oz each)", "1 tsp kosher salt"]],
                  ["Pan sauce", ["1 small shallot, minced", "1/2 cup chicken broth"]],
                  ["Optional: herb finish", ["2 tbsp chopped parsley, for garnish"]]],
  "steps": [["Season", "Your paraphrase…"], ["Sear", "…"]],
  "ahead": "…",
  "nutrition": "",
  "technique": [["Why rest the chicken?", "2–3 sentences of real teaching."]],
  "mistakes": ["Common mistake and how to avoid it"],
  "learn": ["What this recipe teaches"]
}
```

- `difficulty` is Everyday, Intermediate or Advanced. Mark estimated times "(est.)".
- `technique`, `mistakes` and `learn` are optional for everyday folders and expected for lessons.
- Leave out `videos`: a separate pass adds and checks them.

## Before you report
Run `python3 setup/tools/validate_recipes.py`. Fix every ERROR in your recipes, and fix any WARN about them that you reasonably can. Warnings about other folders being empty are expected.

## Report back (short)
For each recipe: id, title, source, URL, rating and caveats (blocked sites, swaps and why, trade-offs, allergen variations you dropped). Don't paste the recipes into the report.
