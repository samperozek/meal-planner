"""Loads config.json (copy config.example.json and fill it in). Every personal detail lives there, nowhere in code.

The config file is found at $MEAL_PLAN_CONFIG, else <repo>/config.json.
Relative paths in it are resolved against the config file's folder.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CONFIG_PATH = os.environ.get("MEAL_PLAN_CONFIG", os.path.join(REPO, "config.json"))

if not os.path.exists(CONFIG_PATH):
    raise SystemExit(f"No config found at {CONFIG_PATH}. Copy config.example.json to config.json and fill it in.")
C = json.load(open(CONFIG_PATH))
_base = os.path.dirname(os.path.abspath(CONFIG_PATH))


def path(p):
    return p if os.path.isabs(os.path.expanduser(p)) else os.path.join(_base, p)


NAME = C["cook"]["name"]                                    # the person who cooks and gets the texts
HOUSEHOLD = C["household"]["description"]                   # e.g. "2 adults + 3 young kids"
SERVINGS = C["household"].get("dinner_servings", 4)
DATA = os.path.expanduser(path(C["paths"]["data_dir"]))     # plans, logs and pantry state (keep out of git)
RECIPES = os.path.expanduser(path(C["paths"]["recipes_dir"]))
PLANS = os.path.join(DATA, "Meal_Plans")
STATE = os.path.join(DATA, "state")
os.makedirs(PLANS, exist_ok=True)
os.makedirs(STATE, exist_ok=True)

LAT, LON = C["location"]["lat"], C["location"]["lon"]
PLACE = C["location"]["name"]
CONTACT = C["location"].get("weather_user_agent_contact", "meal-plan-agent")

KITCHEN_LOG_URL = C.get("kitchen_log", {}).get("url", "")
PHONE = C.get("imessage", {}).get("to", "")

POOLS = C["recipes"]["dinner_pools"]                        # {"core": [folders], "sprinkle": [...], ...}
LESSON_FOLDER = C["recipes"].get("lesson_folder")           # optional: a course cooked one lesson a week, in order
LESSON_LABEL = C["recipes"].get("lesson_label", "Lesson")
BREAKFAST = C["recipes"]["breakfast_pool"]                  # {"folder": ..., "section": ...}
LUNCH = C["recipes"]["lunch_pool"]

ORDERS = C.get("orders", {"order1_day": "Sunday", "order2_day": "Thursday", "order2_fill_day": "Wednesday",
                          "order2_dinners": ["Fri", "Sat", "Sun"]})
TWO_ORDERS = C.get("orders", {}).get("two_orders", True)


def is_lesson(rid, cat):
    return bool(LESSON_FOLDER) and cat.get(rid, {}).get("folder") == LESSON_FOLDER
