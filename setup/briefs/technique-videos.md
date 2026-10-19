# Technique-video brief (research agents)

Find 1–2 short **technique** videos for each recipe in your batch: videos that show the recipe's core techniques (its `skills` and `technique` fields), not just any version of the dish. Recipes in the lesson folder (`recipes.lesson_folder` in config.json) come first. Run commands from the kit folder.

## Finding candidates
Plain web search rarely returns YouTube videos, so use the tool:
```
python3 setup/tools/find_videos.py --page <recipe url>        # videos embedded on the recipe's own page
python3 setup/tools/find_videos.py "<technique or dish> <teacher>"   # YouTube search: title, channel, length, URL
```
- **Start with the recipe's own page.** A video from the same creator, of the same recipe, is ideal. Pages also embed ads, cookbook promos and unrelated clips, so keep a video only if it's about this dish **and** comes from the recipe author's own channel.
- Then search for established teachers:
  - Jacques Pépin (KQED/PBS, the Jacques Pépin Foundation, Home Cooking with Jacques Pépin) and Julia Child (official PBS/GBH uploads)
  - America's Test Kitchen and Cook's Country, King Arthur Baking, NYT Cooking, Serious Eats and J. Kenji López-Alt, the Bon Appétit technique series
  - Chef Jean-Pierre, Gordon Ramsay (official), Food Wishes, Basics with Babish, Ethan Chlebowski
  - Cuisine authorities: Chinese Cooking Demystified, Hot Thai Kitchen, Just One Cookbook, Maangchi, Rick Bayless, Pati Jinich, Lidia Bastianich, Hebbar's Kitchen, Swasthi's Recipes
  - Grilling and smoking: BBQ with Franklin (PBS), Meathead / AmazingRibs, Mad Scientist BBQ
- Brands' own channels are fine, including their TV segments (e.g. ATK's channel). Avoid re-uploads of someone else's show, small anonymous channels and AI-generated content. When a video exists on two official channels, use the original upload.

## What wins when rules conflict
1. It clearly **shows the technique** the recipe teaches.
2. It comes from an **established** teacher or brand.
3. It's **3–20 minutes** long. A short (under 3 min) from the recipe's own creator is fine as one of the two videos, if the other one teaches the technique properly.
4. It's from the **same creator** as the recipe.

## Verify every link (mandatory)
Never guess a URL or video id. Every video must pass `python3 setup/tools/verify_videos.py`, which checks the title and channel against YouTube. For non-YouTube pages (PBS, ATK), only use one if you opened the page and its text clearly offers the video.

## Output
Add a `videos` list to each recipe's JSON file, changing nothing else:

```json
"videos": [{"title": "<exact YouTube title>", "channel": "<exact channel name>", "url": "https://www.youtube.com/watch?v=…",
            "length": "8 min", "why": "One sentence: what to watch for."}]
```

- **`length`:** whole minutes from the tool ("under 1 min" for shorts). If no length is shown, leave out the `length` field but keep the video.
- **`why`:** you usually can't watch the video, so write it from the title, description and recipe, and name what to look for ("Look for how the mustard seeds pop before the chilies go in") without claiming details you haven't seen.
- Use `[]` if no verified, good video exists, and say so in your report.

Then run `python3 setup/tools/verify_videos.py` and fix anything it flags.

## Report back
How many recipes you covered, which are empty, and anywhere you settled (a short clip, a less ideal channel).
