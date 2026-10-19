#!/usr/bin/env bash
# Prepare this machine for meal-plan-agent.
#   bash setup/tools/install.sh           install Python libraries, create config.json, report what's available
#   bash setup/tools/install.sh --check   report only, change nothing
#   bash setup/tools/install.sh --global  also link both skills into ~/.claude/skills (usable from any folder)
set -euo pipefail
KIT="$(cd "$(dirname "$0")/../.." && pwd)"
CHECK=0; GLOBAL=0
for a in "$@"; do
  case "$a" in --check) CHECK=1 ;; --global) GLOBAL=1 ;; esac
done
ok()   { printf "  ✓ %s\n" "$1"; }
todo() { printf "  • %s\n" "$1"; }

echo "meal-plan-agent setup check ($KIT)"

if command -v python3 >/dev/null 2>&1; then ok "Python: $(python3 --version 2>&1)"; else todo "Install Python 3.10+ (https://www.python.org/downloads/)"; exit 1; fi

if python3 -c "import reportlab, openpyxl" >/dev/null 2>&1; then
  ok "Python libraries: reportlab, openpyxl"
elif [ "$CHECK" = 1 ]; then
  todo "Missing Python libraries: run  python3 -m pip install --user reportlab openpyxl"
else
  python3 -m pip install --user --quiet reportlab openpyxl && ok "Installed reportlab and openpyxl"
fi

if [ -f "$KIT/config.json" ]; then
  ok "config.json exists"
elif [ "$CHECK" = 1 ]; then
  todo "No config.json yet (the setup skill creates it)"
else
  cp "$KIT/config.example.json" "$KIT/config.json" && ok "Created config.json from config.example.json (setup fills it in)"
fi

for s in meal-plan meal-plan-setup; do
  [ -f "$KIT/.claude/skills/$s/SKILL.md" ] && ok "Skill /$s is available when this folder is open in Claude Code"
done
if [ "$GLOBAL" = 1 ] && [ "$CHECK" = 0 ]; then
  mkdir -p "$HOME/.claude/skills"
  for s in meal-plan meal-plan-setup; do
    if [ -e "$HOME/.claude/skills/$s" ]; then todo "~/.claude/skills/$s already exists; left as is"
    else ln -s "$KIT/.claude/skills/$s" "$HOME/.claude/skills/$s" && ok "Linked /$s into ~/.claude/skills"; fi
  done
fi

if [ "$(uname)" = "Darwin" ]; then ok "macOS: iMessage texts and scheduled routines are possible"; else todo "Not macOS: texts (iMessage) are unavailable; plans, carts and the Kitchen Log still work"; fi
command -v curl >/dev/null 2>&1 && ok "curl (weather and video checks)" || todo "Install curl"

echo
echo "Also needed inside Claude (the setup skill checks these): Google Calendar and Gmail connectors (read-only),"
echo "Claude in Chrome signed in to your grocery site, and the desktop app's Routines for scheduling."
