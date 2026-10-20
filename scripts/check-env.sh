#!/usr/bin/env bash
# Prints OK / MISSING for everything logo-my-brand needs, with the fix line for each.
ok=0; miss=0
say_ok()   { printf "  OK       %s\n" "$1"; ok=$((ok+1)); }
say_miss() { printf "  MISSING  %s\n           fix: %s\n" "$1" "$2"; miss=$((miss+1)); }

echo "logo-my-brand environment"
command -v python3 >/dev/null 2>&1 && say_ok "python3 ($(python3 --version 2>&1))" || say_miss "python3" "install Python 3.9+ from python.org or brew install python"
python3 -c "import openai" 2>/dev/null && say_ok "openai package" || say_miss "openai package" "pip3 install --user openai"
python3 -c "import PIL" 2>/dev/null && say_ok "Pillow" || say_miss "Pillow" "pip3 install --user pillow"
command -v curl >/dev/null 2>&1 && say_ok "curl" || say_miss "curl" "brew install curl"
if command -v potrace >/dev/null 2>&1; then say_ok "potrace (vector tracing)";
elif python3 -c "import vtracer" 2>/dev/null; then say_ok "vtracer (vector tracing, fallback)";
else say_miss "potrace or vtracer" "brew install potrace   (or: pip3 install --user vtracer)"; fi

KEY="${OPENAI_API_KEY:-}"
for f in ./.env "$HOME/.claude/.env" "$HOME/.env" "${LMB_ENV_FILE:-$HOME/.env}"; do
  [ -z "$KEY" ] && [ -f "$f" ] && KEY=$(grep -E '^OPENAI_API_KEY=' "$f" | head -1 | cut -d= -f2-)
done
[ -n "$KEY" ] && say_ok "OPENAI_API_KEY" || say_miss "OPENAI_API_KEY" "export OPENAI_API_KEY=sk-...   (or put it in ./.env)"

BASE=""
for d in "${LOGO_DESIGN_SKILL:-}" "$HOME/.claude/skills/logo-design" "./.claude/skills/logo-design"; do
  [ -n "$d" ] && [ -f "$d/scripts/render_png.py" ] && BASE="$d" && break
done
[ -n "$BASE" ] && say_ok "logo-design base skill ($BASE)" || say_miss "logo-design base skill" "bash $(dirname "$0")/../install.sh"

if [ -n "$BASE" ]; then
  if python3 -I "$BASE/scripts/render_png.py" --which 2>/dev/null | grep -qiE "chrome|chromium|edge|brave"; then say_ok "a Chromium browser for HTML renders";
  else say_miss "a Chromium browser (Chrome, Chromium, Edge, Brave)" "install Google Chrome; the mockups and the concept sheet are rendered with it"; fi
fi

echo
if [ "$miss" -eq 0 ]; then echo "All $ok checks passed."; exit 0; else echo "$miss missing. Fix the lines above, then run this again."; exit 1; fi
