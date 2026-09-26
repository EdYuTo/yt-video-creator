#!/usr/bin/env bash
# Scaffold a Remotion project next to the raw footage.
#
# usage: setup_project.sh <footage_dir> [project_name]
#   -> <footage_dir>/<project_name>/  (default name: video)
#
# Layout it creates:
#   source/<id>.<ext>      absolute symlinks to the original clips (+ DJI .LRF proxies as <id>.lrf.mp4).
#                          Never served to the browser, only read by ffmpeg (build_edit.py, sheets.py).
#   public/footage/        what the render can see: photos (copied) and, after build_edit.py,
#                          hard-linked or proxied clips. Hard links: Remotion's server 404s on
#                          symlinks leaving public/.
#   media.json             probe output (codec, bit depth, fps, recommended link/proxy per clip)
#   plan.json              edit-plan skeleton with the clip table filled in
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
sed -i.bak "s|__SKILL_DIR__|$SKILL_DIR|" package.json && rm package.json.bak
npm i --silent "remotion@$VERSION" "@remotion/cli@$VERSION" "@remotion/bundler@$VERSION" \
  "@remotion/renderer@$VERSION" "@remotion/google-fonts@$VERSION" react@19 react-dom@19
npm i --silent -D typescript @types/react

id_of() { echo "$1" | tr ' ()' '_--'; }

mkdir -p source public/footage
shopt -s nullglob nocaseglob
for f in "$SRC"/*.{mov,mp4,m4v,mkv,avi,mts,webm}; do
  base="$(basename "$f")"; stem="${base%.*}"; ext="$(echo "${base##*.}" | tr 'A-Z' 'a-z')"
  ln -sfn "$f" "source/$(id_of "$stem").$ext"
done
for f in "$SRC"/*.lrf; do
  base="$(basename "$f")"; stem="${base%.*}"
  ln -sfn "$f" "source/$(id_of "$stem").lrf.mp4"
done
for f in "$SRC"/*.{jpg,jpeg,png,webp}; do
  base="$(basename "$f")"; stem="${base%.*}"; ext="$(echo "${base##*.}" | tr 'A-Z' 'a-z')"
  cp "$f" "public/footage/$(id_of "$stem").$ext"
done
for f in "$SRC"/*.heic; do
  echo "HEIC photo $(basename "$f"): convert to JPEG first (sips -s format jpeg in.heic --out out.jpg)."
done
for f in "$SRC"/*.{mp3,wav,m4a}; do
  echo "Found audio in footage folder: $(basename "$f") — copy it to public/music.<ext> if it is the soundtrack."
done

python3 "$SKILL_DIR/scripts/probe.py" source --project . --json media.json >/dev/null
python3 - <<'EOF'
import json, os
media = json.load(open("media.json"))
clips = {}
for m in media:
    if m["kind"] != "video" or m["file"].endswith(".lrf.mp4"):
        continue
    cid = os.path.splitext(m["file"])[0]
    c = {"file": m["file"], "media": m.get("media", "link"), "dur": m["dur"], "audio": m["audio"]}
    if os.path.exists(f"source/{cid}.lrf.mp4"):
        c["lrf"] = f"{cid}.lrf.mp4"
    clips[cid] = c
plan = {
    "fps": 30,
    "clips": clips,
    "language": None,
    "words": "transcripts/words.json",
    "silence": {"pad": [0.2, 0.3], "gap": 0.75},
    "loudnorm": True,
    "blur": [],
    "long": {"sections": [], "post": []},
    "short": {"sections": []},
}
json.dump(plan, open("plan.json", "w"), indent=1)
print(f"plan.json: {len(clips)} clips")
EOF

echo
echo "Remotion $VERSION project ready: $PROJ"
python3 "$SKILL_DIR/scripts/probe.py" source --project . | tail -n +1
