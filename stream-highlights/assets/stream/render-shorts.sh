#!/usr/bin/env bash
# Render stream Shorts through render.mjs (versioned outputs, shorts.json snapshotted with each).
#   ./render-shorts.sh                 # every short in shorts-data.json
#   ./render-shorts.sh short-02 short-05 [--note "why"]
set -euo pipefail
cd "$(dirname "$0")"
ids=(); note=()
while [ $# -gt 0 ]; do
  case "$1" in --note) note=(--note "$2"); shift 2 ;; *) ids+=("$1"); shift ;; esac
done
if [ ${#ids[@]} -eq 0 ]; then
  ids=($(node -e 'for (const s of require("./shorts-data.json")) console.log(s.id)'))
fi
for id in "${ids[@]}"; do
  node render.mjs "$id" "out/$id.mp4" --plan shorts.json ${note[@]+"${note[@]}"}
done
