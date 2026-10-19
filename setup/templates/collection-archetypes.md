# Designing the collection: categories and sizing

A collection is a set of **folders** (categories). Each folder feeds one slot in the planner, set in `config.json`:

| Slot | Config key | Used for |
|---|---|---|
| Core weeknight | `recipes.dinner_pools.core` | Most weeknight dinners |
| Sprinkle | `recipes.dinner_pools.sprinkle` | At most one a week each: heritage, a favorite cuisine, adventurous dishes |
| Weekend extra | `recipes.dinner_pools.weekend_extra` | Slower braises, seasonal comfort food, date night, hosting |
| Breakfast / lunch | `recipes.breakfast_pool`, `recipes.lunch_pool` | One batch-prepped recipe each per week |
| Lessons | `recipes.lesson_folder` | The culinary-school sequence (optional) |

Every folder gets a **section** structure too (e.g. Sheet Pan / Skillet / One Pot, or Unit 1 · Foundations). Sections help variety and give the cook a mental map.

## Sizing rules of thumb
- Dishes come back no sooner than every 3 weeks, so the dinner pools need at least 4 × (dinners cooked a week); **40–60** dinners is comfortable.
- Breakfast and lunch rotate through the whole pool before repeating: **6–10 each**.
- A **starter build** of 25–30 recipes is enough to start planning. Grow the rest over the next few weeks.
- Keep any single cuisine to about a quarter of the dinners unless the cook asks otherwise.

## Archetypes (starting points; always tailor)

### Young family, busy weeknights
- **Weeknight Foundations** (core, 15–20): ≤ 20 min hands-on, kid-friendly, teaches a reusable skill (sheet-pan roasting, a pan sauce, a stir-fry)
- **Easy Nights** (core, 15–20): ≤ 15 min hands-on: slow cooker, Instant Pot, sheet pan, one pot
- **Global Favorites** (sprinkle, 10–15): mild versions of curries, tacos, noodles, dumplings
- **Cozy Weekends** (weekend extra, 8–12): braises, soups, roasts, things that make good leftovers
- **High-Protein Breakfasts** and **Meal-Prep Lunches** (6–10 each), if the cook eats from the plan

### Couple who love to cook
- **Weeknight** (core, 20): 30-minute dishes with real technique
- **Global Kitchens** (sprinkle, 20): sections per cuisine
- **Date Night** (weekend extra, 10): steak frites, scallops, risotto, fresh pasta
- **Projects** (weekend extra, 8): breads, braises, smoked meats

### Plant-forward or vegetarian household
- **Weeknight Bowls and Skillets** (core, 20), **Soups and Stews** (core, 10), **Global Vegetarian** (sprinkle, 15), **Weekend Bakes** (weekend extra, 8)
- Protein targets come from legumes, tofu, eggs and dairy; check portion notes.

### Health-focused (e.g. limit red meat and dairy)
- Put the rule in the folder criteria: "red meat and dairy fine but not the bulk"
- Prefer chicken, fish, seafood, turkey and legumes in core. Keep the richer classics in weekend extra.
- High-protein breakfast and lunch pools with per-portion protein in `nutrition`.

### Entertainers
- Add **Hosting** folders by group size (4–6, 6–10, 10+), with mains and showpiece appetizers. Use them as weekend extras when the calendar shows guests.

## What to put in COLLECTION_PLAN.md
For each folder: name, slot, count, sections, criteria (time, difficulty, health, kid-friendliness, equipment), and the dish list with ids (`WK-01`, `GL-01`, `BF-01`, `LU-01`, `CS-1.1`…). Research agents get their batches from this file.
