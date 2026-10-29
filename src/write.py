"""브리핑 원고·캡션 생성 (Anthropic Claude).
결과 JSON: {slot, topic, cards:[{title, body, section?}], caption, hashtags, sources, items}
카드 구성: 표지 / 분야별 카드(경제·사회·정치·주식·코인 중 고른 분야) / 한눈에 보기"""
from __future__ import annotations

import argparse
import json
import os
import re

from .common import ACCOUNT, CATEGORIES, SLOTS, StepError, env, get_logger, retry

log = get_logger("write")
MODEL = os.getenv("LLM_MODEL") or "claude-opus-5-5"
DISCLAIMER = "투자 판단은 본인 책임이며, 본 콘텐츠는 투자 권유가 아닙니다."
CTA = "저장해두고 다시 보세요 · 팔로우하면 하루 4번 받아봐요"

SYSTEM = f"""너는 인스타그램 뉴스 브리핑 카드뉴스 에디터다. 계정 {ACCOUNT}.
규칙:
- 기사 문장을 그대로 베끼지 말고 반드시 자기 말로 재구성한다 (저작권). 원문과 같은 문장 8어절 이상 연속 금지.
- 수치·날짜·고유명사는 제공된 원문(sources)에 있는 것만 쓴다. 원문에서 확인되지 않는 내용은 쓰지 않는다.
- 과장·낚시성 표현, 확인되지 않은 루머 금지.
- 정치 뉴스는 특정 정당·인물에 유리하거나 불리한 평가 없이 사실만 중립적으로 전한다.
- 쉬운 말, 존댓말(~요/~습니다) 통일, 전문용어는 괄호로 짧게 설명.
- 주식·코인 뉴스에서 특정 종목·코인 매수/매도 권유, 가격 예측 금지.
- 출력은 오직 JSON 하나. 마크다운 코드펜스 금지."""

SCHEMA = """{
  "topic": "이번 브리핑 한 줄 요약 (내부 기록용)",
  "cover": {"title": "표지 후킹 제목 (15자 내외, 최대 18자, 강조할 단어는 **단어**)", "body": "부제 (25자 내외, 최대 30자)"},
  "sections": [
    {"category": "분야 코드 (주어진 순서 그대로)", "title": "헤드라인 (최대 22자)", "body": "핵심 2~3줄, 줄바꿈은 \\n, 헤드라인+본문 합 80자 이내"}
  ],
  "summary": ["분야별 한 줄 요약, 주어진 순서대로 분야마다 1개 (각 20자 이내)"],
  "caption_hook": "첫 줄 후킹 문장",
  "caption_summary": ["분야별 한 줄씩, '[분야] 내용' 형식"],
  "hashtags": {"large": ["3개"], "medium": ["5개"], "small": ["5개"]},
  "facts_checked": ["원고에 쓴 수치·날짜·고유명사와 그 근거 출처명"]
}"""


def _client():
    import anthropic
    return anthropic.Anthropic(api_key=env("LLM_API_KEY"))


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("LLM 응답에서 JSON을 찾을 수 없습니다")
    return json.loads(m.group(0))


@retry("write-llm", attempts=3, base_delay=5)
def _ask(messages: list[dict]) -> str:
    # fallbacks="default": 안전 분류기가 거절하면 서버가 같은 요청을 대체 모델로 다시 실행한다.
    resp = _client().beta.messages.create(
        model=MODEL, max_tokens=16000, system=SYSTEM, messages=messages,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"모델이 응답을 거절했습니다: {getattr(resp.stop_details, 'category', None)}")
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def _clen(s: str) -> int:
    return len(re.sub(r"\s", "", s or ""))


def validate(d: dict, categories: list[str]) -> list[str]:
    errs = []
    cover = d.get("cover") or {}
    if len(cover.get("title", "").replace("**", "")) > 18:
        errs.append(f"표지 제목이 너무 깁니다 ({len(cover['title'].replace('**', ''))}자, 최대 18자)")
    if len(cover.get("body", "")) > 30:
        errs.append(f"표지 부제가 너무 깁니다 ({len(cover['body'])}자, 최대 30자)")
    secs = d.get("sections", [])
    got = [s.get("category") for s in secs]
    if got != categories:
        return errs + [f"sections의 category는 정확히 {categories} 순서여야 합니다 (현재 {got})"]
    for s in secs:
        name = CATEGORIES[s["category"]]
        if len(s.get("title", "")) > 22:
            errs.append(f"{name} 헤드라인이 {len(s['title'])}자입니다 (최대 22자)")
        t = len(s.get("title", "")) + len(s.get("body", "").replace("\n", ""))
        if t > 80:
            errs.append(f"{name} 카드가 {t}자입니다 (80자 이내)")
        lines = [x for x in s.get("body", "").split("\n") if x.strip()]
        if not 1 <= len(lines) <= 3:
            errs.append(f"{name} 카드 본문은 2~3줄이어야 합니다")
    summary = d.get("summary", [])
    if len(summary) != len(categories):
        errs.append(f"summary는 분야마다 1개씩 {len(categories)}개여야 합니다 (현재 {len(summary)}개)")
    for x in summary:
        if len(x) > 20:
            errs.append(f"summary 한 줄이 너무 깁니다: '{x}' ({len(x)}자, 최대 20자)")
    tags = d.get("hashtags", {})
    n = sum(len(tags.get(k, [])) for k in ("large", "medium", "small"))
    if not 10 <= n <= 15:
        errs.append(f"해시태그는 10~15개여야 합니다 (현재 {n}개)")
    banned = ["매수하세요", "매도하세요", "사세요", "팔으세요", "무조건", "100% 수익", "대박", "충격", "떡상", "떡락"]
    alltext = json.dumps([cover, secs, summary], ensure_ascii=False)
    for b in banned:
        if b in alltext:
            errs.append(f"금지 표현 포함: {b}")
    return errs


def copy_check(d: dict, sources: list[dict]) -> list[str]:
    """원문과 8어절 이상 연속 일치하는 문장이 있는지 점검."""
    src = " ".join((s.get("summary", "") + " " + s.get("text", "")) for s in sources)
    src_norm = re.sub(r"\s+", " ", src)
    errs = []
    for c in [d.get("cover") or {}, *d.get("sections", [])]:
        words = (c.get("title", "") + " " + c.get("body", "")).split()
        for i in range(len(words) - 7):
            chunk = " ".join(words[i:i + 8])
            if chunk in src_norm:
                errs.append(f"원문과 동일한 구절: '{chunk}' → 자기 말로 바꿔주세요")
                break
    return errs


def build_caption(d: dict, sources: list[dict]) -> tuple[str, list[str]]:
    tags = []
    for k in ("large", "medium", "small"):
        for t in d.get("hashtags", {}).get(k, []):
            t = "#" + t.lstrip("#").replace(" ", "")
            if t not in tags:
                tags.append(t)
    tags = tags[:15]
    names = []
    for s in sources:
        if s["source"] not in names:
            names.append(s["source"])
    parts = [d.get("caption_hook", "").strip(), "", *[f"• {x.strip()}" for x in d.get("caption_summary", [])[:6]], ""]
    parts.append("출처: " + ", ".join(names[:8]))
    parts.append(f"※ {DISCLAIMER}")
    parts += ["", " ".join(tags)]
    cap = "\n".join(parts)
    if len(cap) > 2200:
        cap = cap[:2190] + "…"
    return cap, tags


def _source_block(items: list[dict]) -> str:
    out = []
    for it in items:
        out.append(f"===== [{it['category']}] {it['label']} — 선정 기사: {it['selected']['title']} =====")
        for i, s in enumerate(it["sources"], 1):
            out.append(f"[{i}] {s['source']} — {s['title']}\nURL: {s['url']}\n요약: {s.get('summary', '')}\n"
                       f"본문 일부: {s.get('text', '')[:1500]}")
    return "\n\n".join(out)


def write(collected: dict) -> dict:
    slot = collected["slot"]
    items = collected["items"]
    categories = [it["category"] for it in items]
    sources = [s for it in items for s in it["sources"]]
    order = ", ".join(f"{c}({CATEGORIES[c]})" for c in categories)
    user = (f"슬롯: {SLOTS[slot]['label']} {SLOTS[slot]['time']} 뉴스 브리핑 — 방향: {collected['theme']}\n"
            f"분야 순서: {order}\n\n"
            f"분야마다 아래 선정 기사 1건을 다룹니다. 각 분야의 출처들을 교차 확인해, 출처 2곳 이상에서 일치하거나 "
            f"원문에 명시된 사실만 사용하세요.\n\n{_source_block(items)}\n\n"
            f"카드 구성: 1 표지(이번 브리핑 전체를 아우르는 후킹) / 분야별 카드 {len(items)}장(분야 순서대로) / "
            f"마지막 '한눈에 보기'(summary).\n"
            f"해시태그는 대형 3 + 중형 5 + 소형 5 (총 13개 권장, 10~15개).\n"
            f"다음 JSON 형식으로만 답하세요:\n{SCHEMA}")
    messages = [{"role": "user", "content": user}]
    data = None
    for attempt in range(3):
        text = _ask(messages)
        try:
            data = _parse_json(text)
        except (ValueError, json.JSONDecodeError) as e:
            messages += [{"role": "assistant", "content": text}, {"role": "user", "content": f"JSON 파싱 오류: {e}. 올바른 JSON만 다시 출력하세요."}]
            continue
        errs = validate(data, categories) + copy_check(data, sources)
        if not errs:
            break
        log.info("원고 검증 실패 (%d회): %s", attempt + 1, errs)
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": "다음 문제를 고쳐 전체 JSON을 다시 출력하세요:\n- " + "\n- ".join(errs)}]
    else:
        if data is None or validate(data, categories):
            raise StepError("write", "원고 규칙 검증을 3회 시도했지만 통과하지 못했습니다")
    caption, tags = build_caption(data, sources)
    cards = [{"title": data["cover"].get("title", ""), "body": data["cover"].get("body", "")}]
    cards += [{"title": s.get("title", ""), "body": s.get("body", ""), "section": CATEGORIES[s["category"]]}
              for s in data["sections"]]
    cards.append({"title": "한눈에 보기", "body": "\n".join(x.strip() for x in data["summary"]), "cta": CTA})
    return {
        "slot": slot,
        "category": "briefing",
        "palette": SLOTS[slot]["palette"],
        "topic": data.get("topic", " / ".join(it["selected"]["title"] for it in items)),
        "cards": cards,
        "caption": caption,
        "hashtags": tags,
        "disclaimer": DISCLAIMER,
        "items": [{"category": it["category"], "title": it["selected"]["title"], "reason": it["reason"]} for it in items],
        "sources": [{"source": s["source"], "title": s["title"], "url": s["url"]} for s in sources],
        "facts_checked": data.get("facts_checked", []),
        "model": MODEL,
    }


def shorten(doc: dict, indices: list[int]) -> dict:
    """렌더링 넘침 시 해당 카드를 더 짧게 재요약."""
    target = [{"index": i, **doc["cards"][i]} for i in indices]
    prompt = ("다음 카드뉴스 카드들이 이미지 영역을 넘칩니다. 의미와 사실은 유지하고 각 카드를 약 30% 더 짧게 다시 써주세요. "
              "존댓말 유지. JSON 배열로만 답하세요: [{\"index\":번호,\"title\":...,\"body\":...}]\n"
              + json.dumps(target, ensure_ascii=False))
    text = _ask([{"role": "user", "content": prompt}])
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        raise StepError("write-shorten", "재요약 응답 파싱 실패")
    for c in json.loads(m.group(0)):
        i = int(c["index"])
        doc["cards"][i]["title"] = c.get("title", doc["cards"][i]["title"])
        doc["cards"][i]["body"] = c.get("body", doc["cards"][i]["body"])
    return doc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("collected_json")
    a = ap.parse_args()
    with open(a.collected_json, encoding="utf-8") as f:
        print(json.dumps(write(json.load(f)), ensure_ascii=False, indent=2))
