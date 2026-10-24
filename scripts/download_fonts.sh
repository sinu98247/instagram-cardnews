#!/usr/bin/env bash
# Pretendard woff2 (OFL 1.1) 를 templates/fonts 로 내려받습니다. 이미 있으면 건너뜁니다.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)/templates/fonts"
VER="v1.3.9"
mkdir -p "$DIR"
for w in Regular Bold ExtraBold; do
  f="$DIR/Pretendard-$w.woff2"
  if [ -s "$f" ]; then echo "exists: $f"; continue; fi
  curl -fsSL -o "$f" "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@${VER}/packages/pretendard/dist/web/static/woff2/Pretendard-$w.woff2"
  echo "downloaded: $f"
done
