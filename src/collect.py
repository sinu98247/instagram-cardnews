"""소재 수집: 분야(경제·사회·정치·주식·코인)별 RSS → 최근 12시간 → 점수화 → 최근 중복 제외 → 분야별 1건 선정 (출처 2개 이상)."""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import html
import json
import re
import urllib.parse

import feedparser
import requests
import yaml

from .common import CATEGORIES, CONFIG, SLOTS, StepError, get_logger, load_history, now_kst, retry

log = get_logger("collect")
UA = {"User-Agent": "Mozilla/5.0 (cardnews-bot; +https://github.com)"}
STOP = set("의 가 이 은 는 을 를 에 와 과 도 로 으로 및 the a an of to in on for and with is are at by from as its new".split())


def load_config() -> dict:
    return yaml.safe_load((CONFIG / "sources.yaml").read_text(encoding="utf-8"))


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def tokens(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z0-9]+|[가-힣]{2,}", text.lower())
    return {w for w in words if w not in STOP and len(w) > 1}


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def entry_time(e) -> dt.datetime | None:
    for k in ("published_parsed", "updated_parsed"):
        v = e.get(k)
        if v:
            return dt.datetime.fromtimestamp(calendar.timegm(v), dt.timezone.utc)
    return None


@retry("collect-feed", attempts=3, base_delay=3)
def fetch_feed(url: str):
    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    return feedparser.parse(r.content)


def google_news_url(query: str, hours: int) -> str:
    return (f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}+when:{max(1, hours)}h"
            "&hl=ko&gl=KR&ceid=KR:ko")


def gather(category: str, cfg: dict) -> list[dict]:
    hours = cfg.get("lookback_hours", 12)
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    items = []
    for src in cfg[category]:
        gnews = bool(src.get("google_news"))
        url = google_news_url(src["query"], hours) if gnews else src["url"]
        try:
            feed = fetch_feed(url)
        except StepError as e:
            log.warning("피드 실패 %s: %s", src["name"], e.message)
            continue
        for e in feed.entries:
            t = entry_time(e)
            if not t or t < cutoff:
                continue
            title, source = clean(e.get("title", "")), src["name"]
            if gnews:  # Google News는 항목마다 실제 언론사가 다르고 제목 끝에 " - 언론사"가 붙는다
                source = clean((e.get("source") or {}).get("title", "")) or source
                title = re.sub(rf"\s+-\s+{re.escape(source)}$", "", title)
            items.append({
                "title": title,
                "summary": "" if gnews else clean(e.get("summary", ""))[:600],
                "url": e.get("link", ""),
                "source": source,
                "weight": float(src.get("weight", 1.0)),
                "published": t.isoformat(),
            })
    log.info("%s: 최근 %sh 기사 %d건", category, hours, len(items))
    return items


def score(items: list[dict], category: str, cfg: dict) -> list[dict]:
    kws = [k.lower() for k in cfg["keywords"][category]]
    now = dt.datetime.now(dt.timezone.utc)
    for it in items:
        text = (it["title"] + " " + it["summary"]).lower()
        kw = sum(1 for k in kws if k in text)
        related = [o for o in items if o is not it and similarity(it["title"] + " " + it["summary"][:120],
                                                                  o["title"] + " " + o["summary"][:120]) >= 0.18]
        coverage = len({o["source"] for o in related} - {it["source"]})
        age_h = (now - dt.datetime.fromisoformat(it["published"])).total_seconds() / 3600
        recency = max(0.0, 1 - age_h / 12)
        it["related"] = [{"title": o["title"], "url": o["url"], "source": o["source"], "summary": o["summary"]}
                         for o in related][:5]
        # 화제성(다매체 보도) + 중요도(소스 가중치·키워드) + 관심도(최신성)
        it["score"] = round(coverage * 3 + min(kw, 5) * 1.0 + it["weight"] * 2 + recency * 2, 3)
        it["score_detail"] = {"coverage": coverage, "keywords": kw, "weight": it["weight"], "recency": round(recency, 2)}
    items.sort(key=lambda x: x["score"], reverse=True)
    # 같은 사건의 중복 후보 제거
    uniq = []
    for it in items:
        if all(similarity(it["title"], u["title"]) < 0.4 for u in uniq):
            uniq.append(it)
    return uniq[: cfg.get("max_candidates", 20)]


def recent_topics(days: int) -> list[str]:
    cutoff = (now_kst() - dt.timedelta(days=days)).date().isoformat()
    out = []
    for h in load_history():
        if h.get("date", "") >= cutoff and h.get("status") in ("published", "preview"):
            out += [it.get("title", "") for it in h.get("items", [])] or [h.get("topic", "") + " " + h.get("source_title", "")]
    return out


def same_publisher(a: str, b: str) -> bool:
    na, nb = re.sub(r"\W|블로그|blog|news|뉴스", "", a.lower()), re.sub(r"\W|블로그|blog|news|뉴스", "", b.lower())
    return bool(na and nb) and (na in nb or nb in na)


def publishers(sources: list[dict]) -> int:
    uniq: list[str] = []
    for s in sources:
        if not any(same_publisher(s["source"], u) for u in uniq):
            uniq.append(s["source"])
    return len(uniq)


def find_second_source(title: str, exclude: str) -> dict | None:
    """관련 보도가 1건뿐이면 Google News RSS 검색으로 교차 확인용 출처를 찾는다."""
    q = urllib.parse.quote(" ".join(list(tokens(title))[:6]))
    lang = "hl=ko&gl=KR&ceid=KR:ko" if re.search(r"[가-힣]", title) else "hl=en-US&gl=US&ceid=US:en"
    try:
        feed = fetch_feed(f"https://news.google.com/rss/search?q={q}+when:1d&{lang}")
    except StepError:
        return None
    for e in feed.entries[:10]:
        src = clean(e.get("source", {}).get("title", "")) if e.get("source") else ""
        if src and not same_publisher(src, exclude) and similarity(title, clean(e.title)) >= 0.2:
            return {"title": clean(e.title), "url": e.link, "source": src, "summary": clean(e.get("summary", ""))[:300]}
    return None


def fetch_article_text(url: str, limit: int = 3000) -> str:
    """원문 대조용 본문 일부 (실패 시 빈 문자열). 원고에 그대로 쓰지 않고 사실 확인에만 사용."""
    try:
        r = requests.get(url, headers=UA, timeout=15)
        if r.status_code != 200 or "html" not in r.headers.get("Content-Type", ""):
            return ""
        body = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", r.text)
        paras = re.findall(r"(?is)<p[^>]*>(.*?)</p>", body)
        text = " ".join(clean(p) for p in paras if len(clean(p)) > 30)
        return text[:limit]
    except requests.RequestException:
        return ""


def pick(category: str, cfg: dict, avoid: list[str]) -> dict | None:
    """분야 하나에서 최근 중복·다른 분야와 겹침을 피하고 출처 2곳 이상 교차 확인된 기사 1건 선정."""
    items = gather(category, cfg)
    if not items:
        log.warning("%s: 최근 %sh 내 수집된 기사가 없습니다", category, cfg.get("lookback_hours", 12))
        return None
    cands = score(items, category, cfg)
    for c in cands:
        if any(similarity(c["title"], p) >= 0.35 for p in avoid):
            log.info("최근 게시·다른 분야와 중복으로 제외: %s", c["title"])
            continue
        sources = [{"title": c["title"], "url": c["url"], "source": c["source"], "summary": c["summary"]}]
        for r in c["related"]:
            if r["url"] not in {s["url"] for s in sources}:
                sources.append(r)
        if publishers(sources) < 2:
            extra = find_second_source(c["title"], c["source"])
            if extra:
                sources.append(extra)
        if publishers(sources) < 2:
            log.info("교차 확인 출처 부족으로 제외: %s", c["title"])
            continue
        for s in sources[:3]:
            s["text"] = fetch_article_text(s["url"], limit=1500)
        return {
            "category": category,
            "label": CATEGORIES[category],
            "selected": {k: c[k] for k in ("title", "summary", "url", "source", "published", "score", "score_detail")},
            "reason": f"다매체 보도 {c['score_detail']['coverage']}곳, 키워드 {c['score_detail']['keywords']}개, "
                      f"소스 가중치 {c['weight']}, 최신성 {c['score_detail']['recency']} → 점수 {c['score']}",
            "sources": sources[:3],
            "candidates": [{"title": x["title"], "source": x["source"], "score": x["score"]} for x in cands],
        }
    log.warning("%s: 중복·교차확인 조건을 통과한 기사가 없습니다", category)
    return None


def collect(slot: str) -> dict:
    cfg = load_config()
    avoid = recent_topics(cfg.get("dedupe_days", 3))
    picked = []
    for category in CATEGORIES:
        it = pick(category, cfg, avoid)
        if it:
            picked.append(it)
            avoid.append(it["selected"]["title"])  # 같은 사건이 두 분야에 동시에 실리지 않게
    min_items = cfg.get("min_categories", 3)
    if len(picked) < min_items:
        raise StepError("collect", f"기사를 고른 분야가 {len(picked)}개뿐입니다 (최소 {min_items}개)")
    return {"slot": slot, "theme": SLOTS[slot]["theme"], "items": picked}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", choices=list(SLOTS), required=True)
    a = ap.parse_args()
    print(json.dumps(collect(a.slot), ensure_ascii=False, indent=2))
