# Recipe format

Put one JSON file per recipe anywhere under `recipes_dir` (subfolders are fine). A file may also hold a JSON list of recipes. The samples here are short originals written for this repo, so replace them with your own collection.

**Only add recipes you have the right to use.** If you build your collection from published recipes, keep it private, and keep `recipes_dir` out of any public repo.

```json
{
  "id": "WK-01",
  "folder": "Weeknight",
  "section": "Sheet Pan",
  "title": "Sheet-Pan Lemon Chicken Thighs and Potatoes",
  "serves": "4",
  "ingredients": [["Main", ["2 lb boneless skinless chicken thighs", "3 Tbsp olive oil", "1 tsp kosher salt"]]],
  "steps": [["Heat the oven", "Heat to 425°F."], ["Roast", "Roast 35–40 minutes."]],

  "cuisine": "Mediterranean",
  "difficulty": "Everyday",
  "prep": "10 min", "cook": "40 min", "total": "50 min",
  "adapted": "Scaling note shown with the recipe",
  "ahead": "Make-ahead / storage note (used for batch-prep planning)",
  "nutrition": "Portion note, e.g. 'About 30 g protein each'",
  "url": "https://… (original recipe, if any)",
  "source": "Where it came from",
  "pdf": "relative/or/absolute/path/to/your.pdf",
  "rating": 4,
  "videos": [{"title": "Knife skills basics", "channel": "Channel name", "url": "https://www.youtube.com/watch?v=…", "length": "4 min", "why": "What to watch for"}]
}
```

Notes:
- **Required fields:** `id`, `folder`, `section`, `title`, `serves`, `ingredients` and `steps`. The fields after the blank line in the example are optional.
- **`folder`** connects a recipe to `config.json`: the `recipes.dinner_pools` folders, `recipes.lesson_folder`, and `recipes.breakfast_pool` / `lunch_pool` (folder + section).
- **Lesson ids** are ordered by the numbers in them (`CS-1.1`, `CS-1.2`, `CS-2.1`, …).
- **Ingredient lines** should start with a quantity and unit ("2 tsp …", "1/3 cup …", "1 ½ Tbsp …"). That's how the pantry tracker estimates usage.
