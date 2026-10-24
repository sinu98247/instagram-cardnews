# instagram-cardnews — @s_98247 카드뉴스 자동 게시

하루 4회(KST 08:30 / 12:30 / 18:00 / 20:00) **소재 수집 → 원고 작성(Claude) → 카드 이미지 렌더링 → 인스타 캐러셀 게시 → 기록·텔레그램 알림**을 GitHub Actions로 자동 실행합니다.

| 슬롯 | 게시 목표 | cron (UTC) | 주제 | 팔레트 |
|---|---|---|---|---|
| morning (아침) | 08:30 | `12 23 * * *` | 경제·시장 모닝 브리핑 | 네이비+골드 |
| lunch (점심) | 12:30 | `12 3 * * *` | AI·테크 핫이슈 | 다크+퍼플/시안 |
| evening (퇴근) | 18:00 | `42 8 * * *` | 경제·재테크 | 네이비+골드 |
| night (저녁) | 20:00 | `42 10 * * *` | AI·테크 실용 | 다크+퍼플/시안 |

cron은 15~18분 일찍 돌고, 준비가 끝나면 **목표 시각까지 기다렸다가** 게시합니다(최대 30분). 실행 시각으로 슬롯을 판별하며, 수동 실행 시 슬롯을 직접 고를 수 있습니다.

## 구조
```
.github/workflows/post.yml       # 4회 스케줄 + 수동 실행
.github/workflows/insights.yml   # 매주 일요일 09:00(KST) 주간 성과
config/sources.yaml              # RSS 소스·키워드·기간 설정
src/collect.py   # RSS 수집(12시간) → 점수화 → 7일 중복 제외 → 출처 2곳 이상 교차확인
src/write.py     # Claude로 6장 원고 + 캡션/해시태그(JSON), 규칙 자동 검증·재작성
src/render.py    # Playwright로 1080×1350 JPEG(q90) 렌더, 폰트 단계 축소·넘침 점검
src/publish.py   # Graph API 캐러셀 게시 (URL 200/jpeg 확인, 상태 폴링, 한도 확인)
src/token.py     # 토큰 만료 점검, 10일 이하면 갱신 + GitHub Secret 자동 업데이트
src/notify.py    # 텔레그램 알림/미리보기
src/insights.py  # 최근 7일 좋아요·저장·도달 요약 JSON
src/main.py      # 전체 오케스트레이션 (재시도, 슬롯 잠금, 실패 알림)
templates/       # card.html, style.css, fonts/(Pretendard, OFL)
output/YYYY-MM-DD/슬롯/  # 생성 이미지(공개 URL용으로 커밋)
data/history.json        # 게시 이력(중복·잠금)
samples/                 # 렌더 테스트용 원고 샘플
```

> `src/token.py`는 파이썬 표준 모듈 이름과 같아서 **반드시 `python -m src.xxx` 형태로 실행**합니다.

---

## 1. Meta 개발자 앱 설정

### 1-1. 사전 준비
1. 인스타 앱 → 설정 → 계정 유형에서 **@s_98247 을 프로페셔널(비즈니스 또는 크리에이터) 계정**으로 전환합니다.
2. Facebook **페이지**를 하나 만들고(이미 있으면 생략), 페이지 설정 → 연결된 계정 → Instagram에서 @s_98247 을 연결합니다.

### 1-2. 앱 만들기
1. https://developers.facebook.com → 내 앱 → **앱 만들기**.
2. 사용 사례: **"기타"** → 앱 유형 **"비즈니스"** 선택 (화면에 "Instagram 관리/콘텐츠 게시" 사용 사례가 보이면 그것을 선택해도 됩니다).
3. 앱 대시보드에서 **Instagram Graph API**(“Facebook 로그인을 통한 Instagram API”) 와 **Facebook 로그인** 제품을 추가합니다.
4. 앱 설정 → 기본 설정에서 **앱 ID**(= `META_APP_ID`)와 **앱 시크릿**(= `META_APP_SECRET`)을 확인합니다.
5. 본인 계정만 쓰는 경우 앱은 **개발 모드** 그대로 사용해도 됩니다 (앱 관리자 본인 계정에는 권한이 바로 적용됩니다). 다른 사람 계정에도 쓰려면 앱 검수가 필요합니다.

### 1-3. 필요한 권한
| 권한 | 용도 |
|---|---|
| `instagram_basic` | 인스타 계정·미디어 읽기 |
| `instagram_content_publish` | 게시물 업로드 |
| `pages_show_list` | 연결된 페이지 목록 |
| `pages_read_engagement` | 페이지→인스타 계정 연결 정보 조회 |
| `business_management` | 비즈니스 자산 접근(비즈니스 관리자 소유 페이지일 때) |
| `instagram_manage_insights` | 주간 성과(도달·저장) 조회 |

## 2. 장기 액세스 토큰 발급 (단계별)
1. https://developers.facebook.com/tools/explorer (Graph API 탐색기) 접속 → 오른쪽에서 **방금 만든 앱** 선택.
2. "사용자 또는 페이지" → **사용자 토큰** 선택 → "권한 추가"에서 위 6개 권한을 체크 → **Generate Access Token** → 페이스북 로그인 창에서 페이지와 인스타 계정을 모두 허용.
   - 이 토큰은 1~2시간짜리 **단기 토큰**입니다.
3. 장기 토큰(약 60일)으로 교환 — 터미널에서 (값은 직접 바꿔 넣으세요, 이 명령을 남과 공유하지 마세요):
   ```bash
   curl -G "https://graph.facebook.com/v23.0/oauth/access_token" \
     -d grant_type=fb_exchange_token \
     -d client_id=앱ID \
     -d client_secret=앱시크릿 \
     -d fb_exchange_token=단기토큰
   ```
   응답의 `access_token` 이 **장기 토큰**(= `IG_ACCESS_TOKEN`)입니다.
4. 인스타 비즈니스 계정 ID(= `IG_USER_ID`) 찾기:
   ```bash
   curl -G "https://graph.facebook.com/v23.0/me/accounts" -d fields=name,instagram_business_account -d access_token=장기토큰
   ```
   연결한 페이지의 `instagram_business_account.id` (보통 1784…로 시작하는 숫자)가 `IG_USER_ID` 입니다.
5. 확인: 탐색기 상단의 ⓘ 또는 https://developers.facebook.com/tools/debug/accesstoken 에 장기 토큰을 넣고 만료일·권한을 확인합니다.

이후에는 `src/token.py`가 매 실행마다 만료일을 확인하고, **10일 이하로 남으면 자동 갱신 후 GitHub Secret을 업데이트**합니다. 실패하면 텔레그램으로 경고가 옵니다.

## 3. 텔레그램 봇 만들기
1. 텔레그램에서 **@BotFather** 검색 → `/newbot` → 봇 이름, 아이디(…_bot) 입력 → 받은 토큰이 `TELEGRAM_BOT_TOKEN`.
2. 만든 봇과의 대화방을 열고 아무 메시지(예: `hi`)를 보냅니다.
3. 브라우저에서 `https://api.telegram.org/bot<토큰>/getUpdates` 접속 → `"chat":{"id": 123456789 …}` 숫자가 `TELEGRAM_CHAT_ID`.

## 4. GitHub 저장소·Secrets 등록
1. GitHub에 **public** 저장소 `instagram-cardnews` 를 만들고 이 폴더를 푸시합니다.
   ```bash
   git init && git add . && git commit -m "init" && git branch -M main
   git remote add origin https://github.com/<아이디>/instagram-cardnews.git && git push -u origin main
   ```
2. **GH_PAT 만들기**: GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate
   - Repository access: *Only select repositories* → instagram-cardnews
   - Permissions → Repository → **Secrets: Read and write** (Metadata: Read 자동)
3. 저장소 → Settings → **Secrets and variables → Actions → New repository secret** 로 아래 8개 등록:

| 이름 | 값 |
|---|---|
| `IG_USER_ID` | 2-4의 인스타 비즈니스 계정 ID |
| `IG_ACCESS_TOKEN` | 2-3의 장기 토큰 |
| `META_APP_ID` | 앱 ID |
| `META_APP_SECRET` | 앱 시크릿 |
| `LLM_API_KEY` | Anthropic API 키 (https://console.anthropic.com → API Keys) |
| `TELEGRAM_BOT_TOKEN` | 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 채팅 ID |
| `GH_PAT` | 위에서 만든 토큰 |

4. 같은 화면의 **Variables** 탭에서 (선택):
   - `REVIEW_MODE` = `true` (초기 2주 권장, 기본값도 true)
   - `LLM_MODEL` = 사용할 Claude 모델 ID (미설정 시 `claude-sonnet-4-5`)
   - `GRAPH_API_VERSION` = 예: `v23.0`
5. Settings → Actions → General → Workflow permissions: **Read and write permissions** 선택.

## 5. 첫 수동 테스트 (반드시 REVIEW_MODE=true 먼저)
1. Actions 탭 → **Post card news** → Run workflow → `slot`: 예) lunch, `review_mode`: **true** → 실행.
2. 수 분 뒤 텔레그램으로 카드 6장 + 캡션 미리보기가 옵니다. 인스타에는 올라가지 않습니다. (history에 `preview`로 기록되어 같은 슬롯 자동 실행은 건너뜁니다.)
3. 미리보기가 괜찮으면 → Run workflow → 같은 `slot`, `publish_preview`: **체크** → 그 결과물을 실제 게시합니다. 텔레그램으로 게시 링크가 옵니다.
4. 마음에 들지 않으면 아무것도 하지 않으면 됩니다(건너뜀).
5. 2주 정도 안정적이면 Variables의 `REVIEW_MODE` 를 `false` 로 바꾸면 완전 자동 게시로 전환됩니다.

> 검수 모드에서 30분 동안 텔레그램 승인을 기다리는 방식은 Actions 사용 시간을 아끼기 위해 쓰지 않았습니다. "미리보기 → 원하면 publish_preview로 수동 게시" 방식입니다.

### 로컬에서 렌더링만 테스트
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt && python -m playwright install chromium
bash scripts/download_fonts.sh
python -m src.render samples/sample_tech.json --out output/_tmp/tech
```

## 6. 안전장치
- 각 단계 최대 2회 재시도(지수 백오프), 최종 실패 시 텔레그램 `[슬롯, 실패 단계, 에러]` 알림 후 해당 슬롯 건너뜀.
- `data/history.json` 으로 **같은 날 같은 슬롯 중복 게시 금지** (`force` 로만 해제).
- 게시 직전 `content_publishing_limit` 으로 24시간 한도 확인.
- 비밀값은 Secrets에만 두며, 로그는 자동 마스킹합니다.
- 원고 규칙: 원문 8어절 이상 연속 복사 감지 시 재작성, 출처 2곳 이상 교차 확인, 경제 슬롯은 마지막 카드·캡션에 "투자 판단은 본인 책임" 문구 자동 포함, 매수·매도 권유/낚시성 표현 차단.

## 7. 주간 성과
`insights.yml` 이 매주 일요일 09:00(KST)에 최근 7일 게시물의 좋아요·저장·도달을 `data/insights/날짜.json` 으로 저장하고 텔레그램으로 요약을 보냅니다. (`instagram_manage_insights` 권한 필요)
