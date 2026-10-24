"""Instagram Graph API 캐러셀 업로드: 자식 컨테이너 → 캐러셀 컨테이너 → 상태 폴링 → media_publish."""
from __future__ import annotations

import os
import time

import requests

from .common import StepError, env, get_logger, mask, retry

log = get_logger("publish")
GRAPH = f"https://graph.facebook.com/{os.getenv('GRAPH_API_VERSION', 'v23.0')}"


def _check(r: requests.Response, step: str) -> dict:
    try:
        d = r.json()
    except ValueError:
        d = {}
    if not r.ok or "error" in d:
        msg = d.get("error", {}).get("message", r.text[:300])
        raise RuntimeError(f"{step} HTTP {r.status_code}: {mask(msg)}")
    return d


def verify_urls(urls: list[str]) -> None:
    """각 URL이 HTTP 200 + image/jpeg 인지 확인 (raw.githubusercontent 반영 지연 대비 재시도)."""
    for u in urls:
        ok = False
        for i in range(8):
            try:
                r = requests.head(u, timeout=20, allow_redirects=True)
                ctype = r.headers.get("Content-Type", "")
                if r.status_code == 200 and ctype.startswith("image/jpeg"):
                    ok = True
                    break
                log.info("URL 대기 (%d) %s → %s %s", i + 1, u, r.status_code, ctype)
            except requests.RequestException as e:
                log.info("URL 확인 오류: %s", mask(e))
            time.sleep(10)
        if not ok:
            raise StepError("verify-url", f"이미지 URL 확인 실패: {u}")


@retry("publish-limit")
def publishing_limit(ig: str, token: str) -> tuple[int, int]:
    r = requests.get(f"{GRAPH}/{ig}/content_publishing_limit",
                     params={"fields": "config,quota_usage", "access_token": token}, timeout=30)
    d = _check(r, "content_publishing_limit").get("data", [{}])[0]
    return int(d.get("quota_usage", 0)), int(d.get("config", {}).get("quota_total", 50))


@retry("publish-child")
def create_child(ig: str, token: str, url: str) -> str:
    r = requests.post(f"{GRAPH}/{ig}/media", data={"image_url": url, "is_carousel_item": "true", "access_token": token}, timeout=60)
    return _check(r, "child container")["id"]


@retry("publish-carousel")
def create_carousel(ig: str, token: str, children: list[str], caption: str) -> str:
    r = requests.post(f"{GRAPH}/{ig}/media", data={"media_type": "CAROUSEL", "children": ",".join(children),
                                                   "caption": caption, "access_token": token}, timeout=60)
    return _check(r, "carousel container")["id"]


def wait_finished(cid: str, token: str, interval: int = 10, timeout: int = 300) -> None:
    start = time.time()
    while time.time() - start <= timeout:
        r = requests.get(f"{GRAPH}/{cid}", params={"fields": "status_code,status", "access_token": token}, timeout=30)
        d = _check(r, "container status")
        st = d.get("status_code")
        log.info("컨테이너 %s 상태: %s", cid, st)
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise StepError("publish-status", f"컨테이너 {st}: {d.get('status', '')}")
        time.sleep(interval)
    raise StepError("publish-status", "컨테이너가 5분 내 FINISHED 되지 않았습니다")


@retry("publish-media")
def media_publish(ig: str, token: str, cid: str) -> str:
    r = requests.post(f"{GRAPH}/{ig}/media_publish", data={"creation_id": cid, "access_token": token}, timeout=60)
    return _check(r, "media_publish")["id"]


@retry("publish-permalink")
def permalink(mid: str, token: str) -> str:
    r = requests.get(f"{GRAPH}/{mid}", params={"fields": "permalink", "access_token": token}, timeout=30)
    return _check(r, "permalink").get("permalink", "")


def publish(urls: list[str], caption: str, publish_at=None) -> dict:
    ig, token = env("IG_USER_ID"), env("IG_ACCESS_TOKEN")
    if not 2 <= len(urls) <= 10:
        raise StepError("publish", f"캐러셀 이미지 수 오류: {len(urls)}")
    children = [create_child(ig, token, u) for u in urls]
    for c in children:
        wait_finished(c, token)
    cid = create_carousel(ig, token, children, caption)
    wait_finished(cid, token)
    # 목표 시각보다 일찍 준비됐다면 목표 시각까지 대기 (cron 조기 실행 보정)
    if publish_at is not None:
        import datetime as dt
        wait = (publish_at - dt.datetime.now(publish_at.tzinfo)).total_seconds()
        if 0 < wait <= 30 * 60:
            log.info("게시 목표 시각까지 %.0f초 대기", wait)
            time.sleep(wait)
    used, total = publishing_limit(ig, token)
    log.info("게시 한도: %d/%d", used, total)
    if used >= total:
        raise StepError("publish-limit", f"24시간 게시 한도 초과 ({used}/{total})")
    mid = media_publish(ig, token, cid)
    return {"media_id": mid, "permalink": permalink(mid, token), "container_id": cid}
