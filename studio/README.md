# 🏢 1인 크리에이티브 스튜디오 — 12층 셋업

이 저장소 하나에 오픈소스 스킬 12개를 "직원"으로 배치해 둔 설정입니다.
Claude Code 로 이 폴더를 열면 바로 쓸 수 있게 플러그인·스킬·MCP 서버가 연결돼 있습니다.

## ⚡ 3단계로 입주하기

```bash
# 1) 마켓플레이스가 없는 스킬(#01, #02) 받기 + 필요한 도구 점검
bash studio/setup.sh

# 2) (선택) Figma 를 쓸 거라면 개인 토큰 설정
export FIGMA_API_KEY=figd_xxx   # Figma → Settings → Security → Personal access tokens

# 3) 이 폴더에서 Claude Code 실행
claude
```

처음 실행하면 Claude Code 가 두 가지를 물어봅니다. 둘 다 **승인**하면 끝입니다.
- `.claude/settings.json` 에 등록된 **플러그인 마켓플레이스 6곳 신뢰 / 플러그인 설치**
- `.mcp.json` 에 등록된 **MCP 서버 4개 사용 승인**

설치 확인: Claude Code 안에서 `/plugin` (플러그인), `/mcp` (MCP 서버), `/skills` (스킬 목록).

## 🗂 층별 직원 배치표

| 층 | 직원 | 오픈소스 | 연결 방식 | 이렇게 시키세요 |
|---|---|---|---|---|
| 01 | Animation Director | [LottieFiles/motion-design-skill](https://github.com/LottieFiles/motion-design-skill) | 스킬 → `setup.sh` | "카드뉴스 표지용 로고 등장 Lottie 애니메이션 만들어줘" |
| 02 | React Video Engineer | [remotion-dev/skills](https://github.com/remotion-dev/skills) | 스킬 → `setup.sh` | "이 카드뉴스 10장을 15초 릴스 영상으로 Remotion 프로젝트 만들어줘" |
| 03 | Game Developer | [CoplayDev/unity-mcp](https://github.com/CoplayDev/unity-mcp) | MCP `unity` (HTTP) | "씬 원점에 큐브 만들고 Rigidbody 붙여줘" |
| 04 | Design Handoff | [GLips/Figma-Context-MCP](https://github.com/GLips/Figma-Context-MCP) | MCP `figma` | "이 Figma 프레임 링크대로 HTML 템플릿 만들어줘" |
| 05 | Motion Engineer | [greensock/gsap-skills](https://github.com/greensock/gsap-skills) | 플러그인 `gsap-skills` | "스크롤하면 카드가 순서대로 넘어가는 GSAP 타임라인 짜줘" |
| 06 | 3D Artist | [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp) | MCP `blender` | "저폴리 사무실 빌딩 씬 만들어줘" |
| 07 | QA Tester | [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) | MCP `playwright` | "방금 만든 페이지 브라우저로 열어서 모바일 화면 확인해줘" |
| 08 | Video Editor | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | 플러그인 `hyperframes` | `/hyperframes` "이 HTML 카드를 9:16 영상으로 렌더링해줘" |
| 09 | Design Critic | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | 플러그인 `impeccable` | `/critique` `/polish` `/bolder` |
| 10 | Product Designer | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 플러그인 `ui-ux-pro-max` | "뷰티 브랜드 카드뉴스용 디자인 시스템 잡아줘" |
| 11 | Creative Director | [anthropics/skills](https://github.com/anthropics/skills) | 플러그인 `example-skills` | frontend-design · canvas-design · algorithmic-art 등 |
| 12 | Chief of Staff | [obra/superpowers](https://github.com/obra/superpowers) | 플러그인 `superpowers` | brainstorming → writing-plans → 실행 흐름 자동 |

## 🔌 앱이 필요한 층 (03 Unity · 06 Blender)

MCP 서버는 등록돼 있지만, 각 앱 안에 브리지 애드온을 **한 번** 설치해야 연결됩니다.
앱이 꺼져 있을 때 `/mcp` 에서 `unity`/`blender` 가 실패로 보이는 건 정상입니다.

**Blender (06층)**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv 가 없다면
uvx mcp-for-blender install-addon                 # Blender 에 애드온 설치
```
Blender → Edit → Preferences → Add-ons → **Interface: MCP for Blender** 활성화.
3D 뷰포트에서 `N` → **MCP for Blender** 탭 (서버가 꺼져 있으면 **Start MCP Server**).

**Unity (03층)** — Unity 2021.3 LTS ~ 6.x
1. Unity → Window → Package Manager → `+` → *Add package from git URL*
   `https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#main`
2. Window → MCP for Unity → 서버 시작 (기본 `http://localhost:8080/mcp`, `.mcp.json` 에 이미 등록됨)

## 🧩 파일 구성

| 파일 | 역할 |
|---|---|
| `.claude/settings.json` | 플러그인 마켓플레이스 6곳 등록 + 플러그인 자동 활성화 (05, 08–12층) |
| `.mcp.json` | MCP 서버 4개: playwright, figma, blender, unity (03, 04, 06, 07층) |
| `studio/setup.sh` | 스킬 2종을 `.claude/skills/` 로 받아오기 (01, 02층) + 도구 점검. 다시 실행하면 최신화 |

## 💡 이 저장소(인스타 카드뉴스)와 함께 쓰는 추천 워크플로

1. **10층** 으로 브랜드 디자인 시스템 → **11층** frontend-design 으로 카드 템플릿 HTML
2. **09층** `/critique` → `/polish` 로 AI 티 제거
3. **07층** Playwright 로 1080×1350 렌더 확인
4. **08층** HyperFrames 또는 **02층** Remotion 으로 카드뉴스를 릴스 영상화
5. 전체 흐름은 **12층** superpowers 가 계획·분배

## 참고

- 각 오픈소스의 라이선스는 해당 저장소를 따릅니다. 외부 스킬 파일은 커밋하지 않고 `setup.sh` 로 받아옵니다.
- 전역(모든 프로젝트)에서 쓰고 싶다면: Claude Code 안에서 `/plugin marketplace add <owner/repo>` 후 `/plugin install`, MCP 는 `claude mcp add --scope user ...`.
- Claude Desktop 앱에서 쓰려면 `.mcp.json` 의 `mcpServers` 블록을 `claude_desktop_config.json` 에 그대로 복사하면 됩니다.
