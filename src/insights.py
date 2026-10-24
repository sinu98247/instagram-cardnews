"""주간 성과 요약: 최근 7일 게시물의 좋아요·저장·도달 → data/insights/YYYY-MM-DD.json"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os

import requests

from .common import DATA, env, get_logger, load_history, mask, now_kst
from . import notify

log = get_logger("insights")
GRAPH = f"https://graph.facebook.com/{os.getenv('GRAPH_API_VERSION', 'v23.0')}"


def media_list(ig: str, token: str, since: dt.datetime) -> list[dict]:
    out, url = [], f"{GRAPH}/{ig}/media"
    params = {"fields": "id,caption,media_type,timestamp,permalink,like_count,comments_count", "limit": 50, "access_token": token}
    while url:
        r = requests.get(url, params=params, timeout=30)
        d = r.json()
        if not r.ok:
            raise RuntimeError(mask(d.get("error", {}).get("message", r.text[:200])))
        stop = False
        for m in d.get("data", []):
            ts = dt.datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
            if ts < since:
                stop = True
                break
            out.append(m)
        url = None if stop else d.get("paging", {}).get("next")
        params = None
    return out


def media_insights(mid: str, token: str) -> dict:
    r = requests.get(f"{GRAPH}/{mid}/insights", params={"metric": "reach,saved,likes,shares,total_interactions", "access_token": token}, timeout=30)
    if not r.ok:
        log.warning("인사이트 조회 실패 %s: %s", mid, mask(r.text[:200]))
        return {}
    return {x["name"]: (x.get("values") or [{}])[0].get("value", x.get("total_value", {}).get("value")) for x in r.json().get("data", [])}


def weekly(days: int = 7) -> dict:
    ig, token = env("IG_USER_ID"), env("IG_ACCESS_TOKEN")
    end = now_kst()
    since = end - dt.timedelta(days=days)
    slots = {h.get("media_id"): h for h in load_history() if h.get("media_id")}
    posts = []
    for m in media_list(ig, token, since):
        ins = media_insights(m["id"], token)
        h = slots.get(m["id"], {})
        posts.append({
            "id": m["id"], "permalink": m.get("permalink"), "timestamp": m["timestamp"],
            "slot": h.get("slot"), "topic": h.get("topic") or (m.get("caption") or "").split("\n")[0][:60],
            "likes": ins.get("likes", m.get("like_count", 0)) or 0, "saves": ins.get("saved", 0) or 0,
            "reach": ins.get("reach", 0) or 0, "shares": ins.get("shares", 0) or 0, "comments": m.get("comments_count", 0),
        })
    def tot(k): return sum(p[k] for p in posts)
    by_slot = {}
    for p in posts:
        s = by_slot.setdefault(p["slot"] or "unknown", {"posts": 0, "likes": 0, "saves": 0, "reach": 0})
        s["posts"] += 1
        for k in ("likes", "saves", "reach"):
            s[k] += p[k]
    for s in by_slot.values():
        s["avg_reach"] = round(s["reach"] / s["posts"], 1) if s["posts"] else 0
        s["save_rate"] = round(s["saves"] / s["reach"] * 100, 2) if s["reach"] else 0
    top = sorted(posts, key=lambda p: (p["saves"], p["reach"]), reverse=True)[:3]
    return {
        "period": {"from": since.date().isoformat(), "to": end.date().isoformat()},
        "totals": {"posts": len(posts), "likes": tot("likes"), "saves": tot("saves"), "reach": tot("reach")},
        "by_slot": by_slot, "top_posts": top, "posts": posts,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--telegram", action="store_true")
    a = ap.parse_args()
    rep = weekly(a.days)
    path = DATA / "insights" / f"{rep['period']['to']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    if a.telegram:
        t = rep["totals"]
        lines = [f"📊 주간 성과 ({rep['period']['from']}~{rep['period']['to']})",
                 f"게시 {t['posts']} · 좋아요 {t['likes']} · 저장 {t['saves']} · 도달 {t['reach']}"]
        lines += [f"- {k}: 평균 도달 {v['avg_reach']}, 저장률 {v['save_rate']}%" for k, v in rep["by_slot"].items()]
        lines += ["TOP: " + p["topic"] + f" (저장 {p['saves']}, 도달 {p['reach']}) {p['permalink']}" for p in rep["top_posts"]]
        notify.send("\n".join(lines))
