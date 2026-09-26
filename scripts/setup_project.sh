#!/usr/bin/env bash
# Scaffold a Remotion project next to the raw footage and link the media into public/.
#
# usage: setup_project.sh <footage_dir> [project_name]
#   -> <footage_dir>/<project_name>/  (default name: video)
#
# Media handling (learned the hard way):
#   - Remotion's render server 404s on symlinks that point outside public/, and relative
#     symlinks break once the bundle forwards public/. Hard links work and cost no disk space.
#   - Hard links need the same filesystem; if `ln` fails we fall back to copying.
#   - Photos are always copied (small, and symlinked images fail to decode in the renderer).
#   - Files are renamed to simple names without spaces: footage/<stem>.<ext lowercased>.
set -euo pipefail

SRC="$(cd "$1" && pwd)"
NAME="${2:-video}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJ="$SRC/$NAME"
VERSION="$(npm view remotion version)"

if [ -e "$PROJ/package.json" ]; then
  echo "Project already exists at $PROJ — not overwriting." >&2
  exit 1
fi

mkdir -p "$PROJ"
cp -R "$SKILL_DIR/assets/template/." "$PROJ/"
mv "$PROJ/gitignore" "$PROJ/.gitignore"
cd "$PROJ"
npm pkg set name="$NAME"
npm i --silent "remotion@$VERSION" "@remotion/cli@$VERSION" "@remotion/bundler@$VERSION" \
  "@remotion/renderer@$VERSION" "@remotion/google-fonts@$VERSION" react@19 react-dom@19
npm i --silent -D typescript @types/react

mkdir -p public/footage
shopt -s nullglob nocaseglob
for f in "$SRC"/*.{mov,mp4,m4v,mkv,avi,mts,webm}; do
  base="$(basename "$f")"
  stem="${base%.*}"; ext="${base##*.}"
  dest="public/footage/$(echo "$stem" | tr ' ()' '_--' )".$(echo "$ext" | tr 'A-Z' 'a-z')
  ln "$f" "$dest" 2>/dev/null || cp "$f" "$dest"
done
for f in "$SRC"/*.{jpg,jpeg,png,webp}; do
  base="$(basename "$f")"
  stem="${base%.*}"; ext="${base##*.}"
  cp "$f" "public/footage/$(echo "$stem" | tr ' ()' '_--' )".$(echo "$ext" | tr 'A-Z' 'a-z')
done
for f in "$SRC"/*.{mp3,wav,m4a}; do
  echo "Found audio in footage folder: $(basename "$f") — copy it to public/music.<ext> if it is the soundtrack."
done

echo
echo "Remotion $VERSION project ready: $PROJ"
ls -la public/footage
