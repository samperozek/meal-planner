---
name: meal-plan-setup
description: First-time setup for meal-plan-agent. Interviews a new cook about their household, diet, tastes, time and goals; designs their recipe categories; builds a private collection of established, published recipes in the repo's format (with research agents); optionally builds a progressive culinary-school curriculum with technique videos; then writes config.json, publishes the Kitchen Log page, creates the scheduled routines and runs a first plan. Use when someone says "set up the meal planner", "build my recipe collection", "/meal-plan-setup", or opens this repo without a config.json.
---

# Meal-plan setup

You're onboarding a **new cook** onto meal-plan-agent. Work in phases and stop for approval at each ✋. `REPO` is this kit folder (the one holding `planner/`, `setup/` and `.claude/skills/`). Everything you learn about the person goes into `config.json` and their private recipe folder, never into tracked repo files.

**Ground rules (repeat them to yourself before every phase):**
- **Established recipes only.** Every recipe is a specific, existing, well-regarded published recipe (named chef, test kitchen, or heavily tested and highly rated site). Never invent one. If no strong published version exists, choose the closest established dish and say so.
- **Respect the source.** Copy ingredient names and quantities exactly as published; write the method in your own words (keep every time, temperature and doneness cue); credit the source with its URL. Keep the collection **private**: it lives in `my-recipes/` (git-ignored) or a folder outside the repo, and is never pushed to a public repo.
- **Allergies are absolute.** A recipe containing a listed allergen never enters the collection, even as an optional ingredient.
- **The cook decides.** Propose, don't impose: categories, counts, curriculum and schedules are confirmed before you build them.
- **Agent safety carries over:** the planner only fills carts (never checks out) and texts only the cook.

Load the reference files as you reach each phase:
- `setup/templates/interview.md`: the question bank (Phase 1)
- `setup/templates/collection-archetypes.md`: category patterns and sizing (Phase 2)
- `setup/briefs/recipe-sourcing.md`: the brief every research agent follows (Phase 3)
- `setup/templates/culinary-school.md` and `setup/briefs/technique-videos.md`: Phase 4

## Phase 0: Check the machine
Run `bash setup/tools/install.sh --check`. It reports Python and the libraries (`reportlab`, `openpyxl`), whether `config.json` exists, and whether the skills are linked. Fix what it reports (`bash setup/tools/install.sh` installs and links). Note which of these this session has, because later phases depend on them: Google Calendar and Gmail connectors, Claude in Chrome, the Artifact tool, scheduled tasks, iMessage on a Mac. Missing ones just turn features off; tell the cook which.

## Phase 1: Interview ✋
Use `setup/templates/interview.md`. Ask in rounds of at most four questions (AskUserQuestion), lead each with a recommended default, and let free-text answers through "Other". Six rounds: household, diet and health, tastes, time and effort, skills and growth, logistics. Then read back a short profile (8–12 lines) and get a yes.

Save the profile as `my-recipes/PROFILE.md` (private) and write the answers into `config.json` (start from `config.example.json`; set `paths.recipes_dir` to `my-recipes`). Fill `diet`, `cooking`, `preferences` and `lessons` from the answers.

## Phase 2: Design the collection ✋
Using `setup/templates/collection-archetypes.md`, propose the cook's categories (folders). For each folder give:
- its job in the week (which `dinner_pools` slot it feeds: core, sprinkle, weekend_extra; or breakfast/lunch pool; or the lesson folder)
- a target count, and selection criteria (hands-on time, difficulty, cuisines, health rules, kid-friendliness, equipment)
- 6–10 example dishes to show the direction (dish *names* only, nothing sourced yet)

Size it to their rotation: with N cooked dinners a week and dishes repeating no sooner than every 3 weeks, the dinner pools together need at least 4×N recipes, and 40–60 is comfortable. Breakfast and lunch pools need 6–10 each. Offer a **starter build** (about 25–30 recipes, enough to plan from tomorrow) with the rest added later, versus the full build at once.

When approved, write `my-recipes/COLLECTION_PLAN.md`: every folder, its section names, the full list of dishes to source with ids (e.g. `WK-01`…, `BF-01`…), and the criteria. Update `config.json` `recipes` (pools, breakfast/lunch pools) to match.

## Phase 3: Build the collection
Split the plan into batches of 5–10 dishes (one folder or section each) and give each to a research agent (Agent tool, run several in parallel). Each agent's prompt is: the full text of `setup/briefs/recipe-sourcing.md`, the cook's `PROFILE.md`, and its batch (ids, folder, section, dish names, criteria, target servings). Agents write one JSON file per recipe into `my-recipes/<Folder>/<id>.json`, reading pages with `setup/tools/fetch_recipe.py` (exact quantities and ratings) as the brief explains.

As each batch lands:
1. `python3 setup/tools/validate_recipes.py` and fix every ERROR (missing fields, allergens, duplicate ids, unparseable files). Review WARNs (ingredient lines without quantities, hands-on time over the cap, missing sources).
2. Spot-check two recipes per batch yourself against their source pages (`python3 setup/tools/fetch_recipe.py <url>` shows the published ingredients).
3. Tell the cook what landed: dish, source, rating, and any swaps the agent made.

When the starter build is done, offer to keep going in the background, or stop and start planning.

## Phase 4: Culinary school (optional) ✋
Only if the cook wants it. Use `setup/templates/culinary-school.md`:
1. Ask the focus (classic French technique, global kitchens, baking and pastry, grilling and smoking, or a mix), the length (8, 12 or 24 modules) and the cadence (weekly, every other week, or on request).
2. Propose the syllabus: modules in a deliberate progression, each with 3–6 lessons. Each lesson names the **technique** it teaches and a classic dish that teaches it. ✋ Confirm.
3. Source each lesson exactly like Phase 3 (same brief; folder = the lesson folder, ids `<PREFIX>-<module>.<lesson>` with a prefix matching the folder, e.g. `CS-1.1`; section = `Module N · Name`). Lessons are cooked as published; fill in `skills`, `technique`, `mistakes` and `learn`. Teaching depth matters more here than anywhere else.
4. Technique videos: run research agents on `setup/briefs/technique-videos.md` (they find candidates with `setup/tools/find_videos.py`) to add 1–2 verified videos per lesson (`videos` field), then `python3 setup/tools/verify_videos.py` and fix anything it flags. Offer the same for the core weeknight folder.
5. Write `my-recipes/SYLLABUS.md` (modules, lessons, techniques, pacing), and set `recipes.lesson_folder`, `recipes.lesson_label` and `lessons.cadence` in `config.json`.

## Phase 5: Recipe PDFs and the Kitchen Log (optional)
- `python3 setup/tools/recipe_pdf.py` renders a clean PDF for every recipe (next to its JSON) and records the path in the recipe. These are what the Kitchen Log's "Open my recipe PDF" button shows.
- Kitchen Log: publish `kitchen-log/index.html` with the Artifact tool as a private page with capabilities `{"db": {"rules": [{"path": "", "read": "view", "write": "owner"}]}, "assets": {}}` (load the artifact-capabilities skill first). Put its URL in `config.json` → `kitchen_log.url`.

## Phase 6: Schedule it ✋
1. Confirm the cook's number for texts, then send one test iMessage with `python3 planner/imessage.py "🍽️ meal-plan-agent is set up"`. macOS asks once whether Claude may control Messages.
2. Show the three routines from `scheduled-tasks/README.md` (Friday plan, Wednesday order 2 if two orders, daily 4 PM text), with times adjusted to the cook's answers. On approval, create them (scheduled-tasks tool if this session has it, otherwise walk the cook through Routines → New routine). Tell them to click **Run now** once on each and choose **Always allow**.

## Phase 7: First plan
`python3 planner/planner.py catalog`, then `python3 planner/planner.py candidates`, check the pools look right, then run `/meal-plan` for the coming week. Walk the cook through the plan text, the cart text, the Kitchen Log and how to rate or skip a meal. Finish with what's next: grow the collection, add videos, adjust the schedule.

## Growing later
"Add 10 more weeknight dinners", "add a hosting folder", "make the lessons every other week": reopen the matching phase, update `COLLECTION_PLAN.md`, `config.json` and the recipes, and re-run the validator.
