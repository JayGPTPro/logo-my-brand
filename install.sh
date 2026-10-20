#!/usr/bin/env bash
# Installs logo-my-brand for Claude Code on this machine:
#   1. the logo-design base skill (kaankiziltug) into ~/.claude/skills/logo-design, if missing
#   2. this skill into ~/.claude/skills/logo-my-brand (a symlink when run from a checkout)
#   3. the environment check
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SKILLS="$HOME/.claude/skills"
mkdir -p "$SKILLS"

if [ ! -f "$SKILLS/logo-design/scripts/render_png.py" ]; then
  echo "Installing the logo-design base skill..."
  TMP="$(mktemp -d)"
  git clone --depth 1 https://github.com/kaankiziltug/logo-design-skill.git "$TMP/repo" >/dev/null 2>&1
  cp -R "$TMP/repo/skills/logo-design" "$SKILLS/logo-design"
  cp "$TMP/repo/LICENSE" "$SKILLS/logo-design/LICENSE"
  rm -rf "$TMP"
  echo "  -> $SKILLS/logo-design"
else
  echo "logo-design base skill already present."
fi

if [ "$HERE" != "$SKILLS/logo-my-brand" ]; then
  if [ -e "$SKILLS/logo-my-brand" ] && [ ! -L "$SKILLS/logo-my-brand" ]; then
    echo "A folder already exists at $SKILLS/logo-my-brand; leaving it alone."
  else
    ln -sfn "$HERE" "$SKILLS/logo-my-brand"
    echo "Linked $SKILLS/logo-my-brand -> $HERE"
  fi
fi

command -v potrace >/dev/null 2>&1 || python3 -c "import vtracer" 2>/dev/null || {
  if command -v brew >/dev/null 2>&1; then echo "Installing potrace..."; brew install potrace >/dev/null 2>&1 || true; fi
}

bash "$HERE/scripts/check-env.sh"
