"""원고·캡션 생성 (Anthropic Claude). 결과 JSON: {slot, topic, cards:[{title, body}], caption, hashtags, sources}"""
from __future__ import annotations

import argparse
import json
import os
import re

from .common import ACCOUNT, SLOTS, StepError, env, get_logger, retry

log = get_logger("write")
MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-5")
DISCLAIMER = "투자 판단은 본인 책임이며, 본 콘텐츠는 투자 권유가 아닙니다."

ROLES = ["표지", "무슨 일인가", "왜 중요한가", "숫자·핵심 데이터", "나에게 미치는 영향", "마무리"]

SYSTEM = f"""너는 인스타그램 카드뉴스 에디터다. 계정 {ACCOUNT}.
규칙:
- 기사 문장을 그대로 베끼지 말고 반드시 자기 말로 재구성한다 (저작권). 원문과 같은 문장 8어절 이상 연속 금지.
- 수치·날짜·고유명사는 제공된 원문(sources)에 있는 것만 쓴다. 원문에서 확인되지 않는 내용은 쓰지 않는다.
- 과장·낚시성 표현, 확인되지 않은 루머 금지.
- 쉬운 말, 존댓말(~요/~습니다) 통일, 전문용어는 괄호로 짧게 설명.
- 경제·재테크 주제에서는 특정 종목·코인 매수/매도 권유 금지.
- 출력은 오직 JSON 하나. 마크다운 코드펜스 금지."""

SCHEMA = """{
  "topic": "주제 한 줄 (내부 기록용)",
  "cards": [
    {"title": "표지 후킹 제목 (15자 내외, 최대 18자)", "body": "부제 (25자 내외, 최대 30자)"},
    {"title": "소제목: 무슨 일인가", "body": "핵심 2~3줄, 줄바꿈은 \\n, 소제목+본문 합 80자 이내"},
    {"title": "소제목: 왜 중요한가", "body": "..."},
    {"title": "소제목: 숫자·핵심 데이터", "body": "..."},
    {"title": "소제목: 나에게 미치는 영향", "body": "..."},
    {"title": "3줄 요약", "body": "요약1\\n요약2\\n요약3", "cta": "저장해두고 다시 보세요 · 팔로우하면 매일 4번 받아봐요"}
  ],
  "caption_hook": "첫 줄 후킹 문장",
  "caption_summary": ["요약 3~5줄"],
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
    resp = _client().messages.create(model=MODEL, max_tokens=3000, system=SYSTEM, messages=messages, temperature=0.4)
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def _clen(s: str) -> int:
    return len(re.sub(r"\s", "", s or ""))


def validate(d: dict) -> list[str]:
    errs = []
    cards = d.get("cards", [])
    if len(cards) != 6:
        return [f"카드는 정확히 6장이어야 합니다 (현재 {len(cards)}장)"]
    if len(cards[0].get("title", "")) > 18:
        errs.append(f"표지 제목이 너무 깁니다 ({len(cards[0]['title'])}자, 최대 18자)")
    if len(cards[0].get("body", "")) > 30:
        errs.append(f"표지 부제가 너무 깁니다 ({len(cards[0]['body'])}자, 최대 30자)")
    for i in range(1, 5):
        t = len(cards[i].get("title", "")) + len(cards[i].get("body", "").replace("\n", ""))
        if t > 80:
            errs.append(f"{i+1}번 카드가 {t}자입니다 (80자 이내)")
        lines = [x for x in cards[i].get("body", "").split("\n") if x.strip()]
        if not 1 <= len(lines) <= 3:
            errs.append(f"{i+1}번 카드 본문은 2~3줄이어야 합니다")
    tags = d.get("hashtags", {})
    n = sum(len(tags.get(k, [])) for k in ("large", "medium", "small"))
    if not 10 <= n <= 15:
        errs.append(f"해시태그는 10~15개여야 합니다 (현재 {n}개)")
    banned = ["매수하세요", "매도하세요", "사세요", "팔으세요", "무조건", "100% 수익", "대박", "충격"]
    alltext = json.dumps(cards, ensure_ascii=False)
    for b in banned:
        if b in alltext:
            errs.append(f"금지 표현 포함: {b}")
    return errs


def copy_check(d: dict, sources: list[dict]) -> list[str]:
    """원문과 8어절 이상 연속 일치하는 문장이 있는지 점검."""
    src = " ".join((s.get("summary", "") + " " + s.get("text", "")) for s in sources)
    src_norm = re.sub(r"\s+", " ", src)
    errs = []
    for c in d.get("cards", []):
        words = (c.get("title", "") + " " + c.get("body", "")).split()
        for i in range(len(words) - 7):
            chunk = " ".join(words[i:i + 8])
            if chunk in src_norm:
                errs.append(f"원문과 동일한 구절: '{chunk}' → 자기 말로 바꿔주세요")
                break
    return errs


def build_caption(d: dict, sources: list[dict], category: str) -> tuple[str, list[str]]:
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
    parts = [d.get("caption_hook", "").strip(), "", *[f"• {x.strip()}" for x in d.get("caption_summary", [])[:5]], ""]
    parts.append("출처: " + ", ".join(names[:3]))
    if category == "econ":
        parts.append(f"※ {DISCLAIMER}")
    parts += ["", " ".join(tags)]
    cap = "\n".join(parts)
    if len(cap) > 2200:
        cap = cap[:2190] + "…"
    return cap, tags


def _source_block(sources: list[dict]) -> str:
    out = []
    for i, s in enumerate(sources, 1):
        out.append(f"[{i}] {s['source']} — {s['title']}\nURL: {s['url']}\n요약: {s.get('summary','')}\n본문 일부: {s.get('text','')[:2000]}")
    return "\n\n".join(out)


def write(collected: dict) -> dict:
    slot = collected["slot"]
    category = collected["category"]
    sources = collected["sources"]
    user = (f"슬롯: {SLOTS[slot]['label']} {SLOTS[slot]['time']} — 주제 방향: {collected['theme']}\n"
            f"선정 기사: {collected['selected']['title']}\n선정 근거: {collected['reason']}\n\n"
            f"아래 출처들을 교차 확인해, 출처 2곳 이상에서 일치하거나 원문에 명시된 사실만 사용하세요.\n\n"
            f"{_source_block(sources)}\n\n"
            f"카드 6장 구성: 1 표지 / 2 무슨 일인가 / 3 왜 중요한가 / 4 숫자·핵심 데이터 / 5 나에게 미치는 영향 / 6 마무리(3줄 요약 + 저장·팔로우 유도).\n"
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
        errs = validate(data) + copy_check(data, sources)
        if not errs:
            break
        log.info("원고 검증 실패 (%d회): %s", attempt + 1, errs)
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": "다음 문제를 고쳐 전체 JSON을 다시 출력하세요:\n- " + "\n- ".join(errs)}]
    else:
        if data is None or validate(data):
            raise StepError("write", "원고 규칙 검증을 3회 시도했지만 통과하지 못했습니다")
    caption, tags = build_caption(data, sources, category)
    cards = [{"title": c.get("title", ""), "body": c.get("body", ""), **({"cta": c["cta"]} if c.get("cta") else {})}
             for c in data["cards"]]
    return {
        "slot": slot,
        "category": category,
        "topic": data.get("topic", collected["selected"]["title"]),
        "cards": cards,
        "caption": caption,
        "hashtags": tags,
        "disclaimer": DISCLAIMER if category == "econ" else "",
        "sources": [{"source": s["source"], "title": s["title"], "url": s["url"]} for s in sources],
        "reason": collected["reason"],
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
