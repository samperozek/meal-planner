# Culinary school: designing the curriculum

A culinary school is an ordered sequence of **lessons**. Each lesson teaches one named technique through a classic, published recipe. The planner schedules the next lesson each week (or every other week) on the most open evening, usually the weekend. It sends the technique videos the evening before, and only counts a lesson as done once the cook logs it as cooked. A skipped lesson comes back the next week.

## Ask first
- **Focus:** classic French technique (the traditional backbone), global kitchens, baking and pastry, grilling and smoking, or a mix.
- **Length:** 8 modules (about 6 months at one lesson a week), 12 modules (about 1 year), or 24 modules (about 2 years, in two "years").
- **Cadence:** weekly, every other week, or on request (`lessons.cadence` in config).
- **Constraints:** diet rules, equipment, altitude (above 3,000 ft, baking and boiling need adjusting, so add notes), and how long a session can run (most lessons should fit 1½–3 hours).

## Progression
Order modules so each one builds on the last. A dependable backbone:

1. **Knife skills and mise en place:** cuts (dice, julienne, brunoise), setting up a station, cooking in stages
2. **Eggs:** scrambles, the French omelet, poaching, a first emulsion (hollandaise or mayonnaise)
3. **Stocks and soups:** white and brown stock, purées, a clear soup
4. **Mother sauces:** béchamel, velouté, tomato, emulsion sauces
5. **Sauté and pan sauces:** searing, fond, deglazing, mounting with butter
6. **Roasting:** a whole bird, roast vegetables, resting and carving
7. **Braising and stewing:** browning, liquid levels, low and slow, finishing the sauce
8. **Fish and shellfish:** pan-searing, en papillote, poaching, mussels and clams
9. **Fresh pasta and dumplings:** egg dough, filled pasta, gnocchi
10. **Bread:** lean dough, enriched dough, shaping, steam and crust
11. **Pastry:** pie and tart dough, pâte à choux, blind baking
12. **Desserts and a capstone menu:** custards, a soufflé, then cooking a full three-course meal

**Second-year options:** vegetables, grains and legumes; live-fire grilling; smoking and barbecue; frying; world kitchens (a module per cuisine); preservation (pickling, fermenting, curing); advanced pastry; a grand capstone.

**Other focuses:** swap in modules per cuisine (global), per dough type (baking), or per cooking method and fuel (grilling and smoking), keeping the same "one technique per lesson, building as you go" structure.

## Each lesson
- id `<PREFIX>-<module>.<lesson>`, where the prefix matches the lesson folder (`CS-1.1` for Culinary_school, `GK-1.1` for Global_Kitchens). Folder = the lesson folder; section `Module 1 · Knife Skills and Mise en Place`
- A **classic dish that teaches the technique** (ratatouille for knife skills, a French omelet for egg control, chicken chasseur for a pan sauce), sourced with `setup/briefs/recipe-sourcing.md`
- Cooked **as published**: the full recipe, with leftovers planned as a meal
- `skills`, `technique` (the why), `mistakes`, and `learn` filled in carefully. This is the teaching.
- Altitude adjustments and other household notes go in `notes`, never in the method. If the source offers several methods, teach the one that fits the cook's equipment and mention the others in `notes`.
- 1–2 verified technique videos (`setup/briefs/technique-videos.md`)

## SYLLABUS.md
List each module with its goal, then its lessons (id, dish, technique, difficulty and time). Add pacing (which month), seasonal notes (grilling in summer, braises in winter) and any altitude notes. The cook can tick lessons off as they go; the cook log records them too.
