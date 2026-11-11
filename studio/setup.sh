#!/usr/bin/env bash
# 스튜디오 셋업: 플러그인 마켓플레이스가 없는 스킬(#01 motion-design, #02 remotion)을
# 프로젝트 .claude/skills/ 로 받아오고, MCP 서버에 필요한 도구가 있는지 점검합니다.
# 다시 실행하면 최신 버전으로 갱신됩니다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$ROOT/.claude/skills"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$SKILLS_DIR"

fetch_skills() {  # $1=owner/repo  $2=repo 안의 skills 경로
  local repo="$1" sub="$2" dest="$TMP/${1//\//_}"
  echo "▶ $repo 받는 중..."
  git clone -q --depth 1 "https://github.com/$repo" "$dest"
  for d in "$dest/$sub"/*/; do
    [ -f "$d/SKILL.md" ] || continue
    local name; name="$(basename "$d")"
    rm -rf "${SKILLS_DIR:?}/$name"
    cp -R "$d" "$SKILLS_DIR/$name"
    echo "  ✓ .claude/skills/$name"
  done
}

fetch_skills LottieFiles/motion-design-skill skills   # #01 Animation Director
fetch_skills remotion-dev/skills skills               # #02 React Video Engineer

echo
echo "▶ MCP 서버 준비 상태 점검"
check() { if command -v "$1" >/dev/null 2>&1; then echo "  ✓ $1"; else echo "  ✗ $1 없음 — $2"; fi; }
check node "Node.js 18+ 설치 필요 (playwright·figma MCP, remotion, hyperframes)"
check npx  "Node.js 와 함께 설치됩니다"
check uvx  "uv 설치: curl -LsSf https://astral.sh/uv/install.sh | sh (blender·unity MCP)"
check ffmpeg "영상 렌더링(hyperframes·remotion)에 권장"
if [ -z "${FIGMA_API_KEY:-}" ]; then
  echo "  ✗ FIGMA_API_KEY 미설정 — figma MCP 사용 시 export FIGMA_API_KEY=... (studio/README.md 참고)"
else
  echo "  ✓ FIGMA_API_KEY"
fi

echo
echo "완료! 이 폴더에서 'claude' 를 실행하면 플러그인 설치와 MCP 서버 승인을 물어봅니다."
echo "Blender/Unity 는 앱 쪽 애드온 설치가 한 번 필요합니다 → studio/README.md"
