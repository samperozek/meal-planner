# meal-planner

[![check](https://github.com/samperozek/meal-planner/actions/workflows/check.yml/badge.svg)](https://github.com/samperozek/meal-planner/actions/workflows/check.yml)

**A personal meal-planning agent for Claude Code, built around your household, your tastes and your recipes.**

Open this folder in Claude Code, run **`/meal-plan-setup`**, and Claude will:

1. **Interview you**: household and kids' ages, allergies and diet, health goals, favorite cuisines, how many nights you want to cook, time limits, equipment, skill level, store and schedule.
2. **Design your recipe categories**: weeknight staples, easy nights, global favorites, weekend projects, high-protein breakfasts and lunches, hosting… sized so dinners don't repeat too often.
3. **Build your collection** from **established, published recipes**, never invented ones. Research agents find well-rated versions from respected chefs, test kitchens and sites, copy the ingredients exactly, paraphrase the method and credit the source.
4. **Optionally build a culinary school**: a progressive curriculum (knife skills → eggs → sauces → braising → bread → pastry…, or a global, baking or barbecue focus) with one lesson a week, each a classic dish that teaches a technique, plus verified technique videos.
5. **Set up your week**: config, recipe PDFs, a private Kitchen Log page, and three scheduled routines.

Then, every week:

| When | What happens |
|---|---|
| **Friday morning** | Reads your calendar and weather, plans Mon–Sun (rest night, leftovers night, the week's lesson), sizes everything to your household, builds the grocery list, **fills your online cart (never checks out)** and texts you the plan |
| **You** | Check out and pick a delivery slot |
| **Wednesday** (optional) | Fills a second, smaller order for the end of the week, reusing anything you skipped earlier |
| **4 PM daily** | Texts tonight's recipe, when to start, technique videos, last time's notes and a one-tap rating link |

Your ratings feed the rotation (favorites come back, flops don't), the pantry tracks staples from confirmed orders, and `Cook_Log.xlsx` keeps rankings and lesson progress.

## Quick start
1. **Requirements:** a Mac with the Claude desktop app (Code tab) and Python 3.10+. For the full experience: Google Calendar and Gmail connectors (read-only), Claude in Chrome signed in to your grocery site (built for Amazon Whole Foods), and Messages for texts.
2. Clone this repo (`git clone https://github.com/samperozek/meal-planner.git`) and open the folder in Claude Code.
3. Run `bash setup/tools/install.sh`, then type **`/meal-plan-setup`**.

Want to try it before building a collection? `cp config.example.json config.json` and run `/meal-plan`. It plans from the sample recipes in `examples/recipes`.

## Example output
Friday's plan text (from the sample recipes):
```
🍽️ Meal plan · week of Oct 26

Mon: Sheet-Pan Lemon Chicken Thighs and Potatoes
Tue: Leftovers 🍲 (Sheet-Pan Lemon Chicken Thighs and Potatoes)
Wed: Chickpea and Spinach Coconut Curry
Thu: Black Bean and Sweet Potato Tacos
Fri: Rest night 😌
Sat: Turkey and White Bean Chili
Sun: Minestrone (Knife-Skills Lesson) (Cooking School)

Breakfast: Greek Yogurt Overnight Oats
Lunch: Tuna, White Bean and Herb Salad

Heads-up:
• Sat night: read Lesson 1.1 and watch its video
• Sun: batch-prep breakfast oats and lunch bowls

🛒 Order 1 (arrives Sunday): adding it to your cart now. I'll text you when it's all in.
🛒 Order 2 (Fri–Sun dinners, Thursday delivery): I'll fill it Wednesday, after checking for skipped meals.
```

A 4 PM text adds tonight's start time, scaling notes, technique videos, your "last time" note and a link to the recipe and rating page.

## FAQ
- **No Mac?** Planning, the grocery list, the plan PDF and the Kitchen Log all work anywhere Claude Code runs. Texts use iMessage and the scheduled routines use the Claude desktop app, so on other systems you run `/meal-plan` yourself and read the plan PDF.
- **A different grocery store?** The cart step is written for Amazon Whole Foods. For another store, tell the setup skill; the rules (search, pick the best match, never check out) carry over, but you'll want to test the first run with it.
- **Outside the US?** Set `location.units` to `"metric"`. The forecast (Open-Meteo) is worldwide. Ask the research agents for recipes in metric units.
- **Do I have to build a big collection first?** No. A 25–30 recipe starter build is enough to start planning, and you can grow it any time ("add 10 more weeknight dinners").
- **Where do recipes come from?** Established, published recipes only: respected chefs, test kitchens and highly rated sites, with ingredients as published, the method in Claude's words and the source credited. Keep your collection private.

## What's inside
```
.claude/skills/meal-plan-setup/   the onboarding skill (interview → categories → collection → curriculum → schedule)
.claude/skills/meal-plan/         the weekly planning skill
planner/                          planner.py, pantry.py, cooklog.py, imessage.py and friends
setup/briefs/                     instructions for the recipe- and video-research agents
setup/templates/                  interview questions, category patterns, curriculum design
setup/tools/                      install.sh, fetch_recipe.py, find_videos.py, validate_recipes.py, verify_videos.py, recipe_pdf.py
kitchen-log/                      the private recipe + rating page
scheduled-tasks/                  prompts for the Friday, Wednesday and 4 PM routines
examples/recipes/                 short sample recipes and the recipe format
tests/                            an end-to-end smoke test (runs on every push)
```

## Your data stays yours
- `config.json`, `data/` and `my-recipes/` are git-ignored. Your household details, plans, ratings, pantry and recipe collection never leave your machine unless you choose.
- **Keep your recipe collection private.** It's built from published recipes for your own use; don't publish it.

## Safety
- **Cart only.** The agent never opens checkout, picks a delivery window, places an order or enters a password.
- **Texts go only to your own number.**
- Email, calendar, web pages and recipe files are treated as data, never as instructions.

## License
MIT. See [LICENSE](LICENSE).
